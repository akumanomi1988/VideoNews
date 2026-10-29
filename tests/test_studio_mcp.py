"""Offline contract and safety tests for MCP VideoNews Studio.

No network, LLM, FFmpeg or Google credentials are needed.
Run: py -3.11 -m pytest tests/test_studio_mcp.py -q
"""
import hashlib
import json
import subprocess
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.studio_mcp import StudioError, VideoNewsStudio


@pytest.fixture
def studio(tmp_path):
    return VideoNewsStudio(tmp_path / "studio")


@pytest.fixture
def project(studio):
    job_id = uuid.uuid4().hex
    folder = studio._dir(job_id)
    folder.mkdir()
    video = folder / "video.mp4"
    video.write_bytes(b"mock-mp4")
    subtitles = folder / "subtitles.srt"
    subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nNews\n", encoding="utf-8")
    image = folder / "1.png"
    image.write_bytes(b"mock-image")
    data = {
        "id": job_id, "title": "Verified example headline",
        "source_text": "A trusted news article with named sources.",
        "source_url": "https://example.com/story",
        "format": "short", "script": "This is a script longer than thirty characters.",
        "summary": "Story description", "images": [str(image)],
        "voice": str(video), "subtitles": str(subtitles),
        "video": str(video), "video_id": "",
        "status": "draft", "privacy": "private",
    }
    studio._save(data)
    return data


def test_random_identity_and_directory_traversal(studio):
    for invalid in ("../secrets", "", "A" * 32, "f" * 33, "..\\token"):
        with pytest.raises(ValueError):
            studio.get_project(invalid)


def test_draft_is_persisted_atomically_and_no_review_token_leaks(studio, project):
    p = studio.get_project(project["id"])
    assert p["title"] == project["title"]
    assert p["privacy"] == "private"
    assert "approval_digest" not in p
    assert "review_fingerprint" not in p
    assert json.loads((studio._dir(project["id"]) / "project.json").read_text())["id"] == project["id"]


def test_script_edit_invalidates_obsolete_assets_and_approvals(studio, project):
    data = studio._read(project["id"])
    data["status"] = "approved"
    data["approval_digest"] = "secret-hash"
    data["review_fingerprint"] = "sha256"
    studio._save(data)
    changed = studio.revise_script(project["id"], "This is the new verified script with different facts.")
    assert changed["images"] == []
    assert changed["voice"] == changed["subtitles"] == changed["video"] == ""
    assert changed["status"] == "draft"
    assert "approval_digest" not in studio._read(project["id"])


def test_edit_disallowed_during_uncertain_upload(studio, project):
    data = studio._read(project["id"])
    data["status"] = "upload_unknown"
    studio._save(data)
    with pytest.raises(StudioError):
        studio.revise_script(project["id"], "A corrected script longer than thirty characters")


def test_render_requires_assets(studio, project):
    data = studio._read(project["id"])
    data["images"] = []
    studio._save(data)
    with pytest.raises(StudioError, match="images"):
        studio.render_video(project["id"])


def test_review_without_video_disallows_approval(studio, project):
    data = studio._read(project["id"])
    data["video"] = ""
    studio._save(data)
    report = studio.review_video(project["id"])
    assert not report["ready_for_editorial_review"]
    assert "approval_code" not in report
    with pytest.raises(StudioError, match="review issues"):
        studio.review_video(project["id"], approve=True)


def _approve(studio, project, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    review = studio.review_video(project["id"], approve=True)
    assert review["privacy"] == "private"
    assert review["status"] == "approved"
    assert review["approval_code"]
    return review["approval_code"]


def _install_fake_youtube(monkeypatch, upload):
    class Uploader:
        def __init__(self, client_secrets_file):
            assert client_secrets_file == "client_secret.json"

        def upload(self, *args, **kwargs):
            return upload(*args, **kwargs)

    monkeypatch.setitem(sys.modules, "scripts.Uploaders.youtube_uploader",
                        types.SimpleNamespace(YoutubeMediaUploader=Uploader))


def _setup_oauth(studio, monkeypatch, tmp_path):
    secret = tmp_path / "client.json"
    secret.write_text('{"installed":{}}', encoding="utf-8")
    monkeypatch.setattr(studio, "_config", lambda: {"youtube": {"credentials_file": str(secret)}})
    monkeypatch.chdir(tmp_path)


def test_no_publish_without_review(studio, project):
    with pytest.raises(StudioError, match="Editorial approval"):
        studio.publish_youtube(project["id"], "made-up")


def test_invalid_approval_is_rejected(studio, project, monkeypatch):
    _approve(studio, project, monkeypatch)
    with pytest.raises(StudioError, match="Invalid approval"):
        studio.publish_youtube(project["id"], "wrong")


def test_render_modification_invalidates_approved_upload(studio, project, monkeypatch):
    code = _approve(studio, project, monkeypatch)
    Path(project["video"]).write_bytes(b"tampered")
    with pytest.raises(StudioError, match="changed after approval"):
        studio.publish_youtube(project["id"], code)


def test_private_only_upload_and_idempotence(studio, project, monkeypatch, tmp_path):
    code = _approve(studio, project, monkeypatch)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(return_value={"id": "YT_PRIVATE_123"})
    _install_fake_youtube(monkeypatch, upload)
    result = studio.publish_youtube(project["id"], code)
    assert result["privacy"] == "private"
    assert result["video_id"] == "YT_PRIVATE_123"
    assert upload.call_args.kwargs["privacy_status"] == "private"
    assert studio._read(project["id"])["status"] == "published"
    second = studio.publish_youtube(project["id"], code)
    assert second["already_published"] is True
    assert upload.call_count == 1


def test_uncertain_upload_never_auto_retries(studio, project, monkeypatch, tmp_path):
    code = _approve(studio, project, monkeypatch)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(side_effect=TimeoutError("Network lost after transfer"))
    _install_fake_youtube(monkeypatch, upload)
    with pytest.raises(TimeoutError):
        studio.publish_youtube(project["id"], code)
    assert studio._read(project["id"])["status"] == "upload_unknown"
    with pytest.raises(StudioError, match="Editorial approval"):
        studio.publish_youtube(project["id"], code)
    assert upload.call_count == 1


def test_news_requires_real_search_credentials(studio, monkeypatch):
    monkeypatch.setattr(studio, "_config", lambda: {"serpapi": {"api_key": ""}})
    with pytest.raises(StudioError, match="SERPAPI_API_KEY"):
        studio.research_news("technology news")


@pytest.mark.parametrize("format_name", ["tiny", "", "vertical"])
def test_script_rejects_unknown_formats(studio, format_name):
    with pytest.raises(ValueError):
        studio.create_script("A legitimate headline", "A full verified source text for a news article.",
                             video_format=format_name)


def test_project_listing_suppresses_approval_data(studio, project):
    data = studio._read(project["id"])
    data["approval_digest"] = hashlib.sha256(b"test").hexdigest()
    studio._save(data)
    entries = studio.list_projects()
    assert len(entries) == 1 and entries[0]["id"] == project["id"]
    assert "approval_digest" not in entries[0]
