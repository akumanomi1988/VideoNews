"""Offline contract and safety tests for MCP VideoNews Studio.

No network, LLM, FFmpeg or Google credentials are needed.
Run: py -3.11 -m pytest tests/test_studio_mcp.py -q
"""
import hashlib
import inspect
import json
import subprocess
import sys
import threading
import time
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


def test_storyboard_edit_keeps_assets_for_unchanged_scenes(studio):
    project = studio.create_project("An example project title")
    initial = [
        {"id": "scene-1", "visual_prompt": "Map of Spain", "visual_type": "graphic"},
        {"id": "scene-2", "visual_prompt": "City skyline", "visual_type": "illustration"},
    ]
    studio.save_storyboard(project["id"], initial)
    image = studio._dir(project["id"]) / "city.png"
    image.write_bytes(b"image")
    data = studio._read(project["id"])
    data["asset_records"] = [{
        "id": "asset-city", "scene_id": "scene-2", "path": str(image),
        "sha256": hashlib.sha256(b"image").hexdigest(),
    }]
    data["storyboard"][1]["asset_ids"] = ["asset-city"]
    data["images"] = [str(image)]
    studio._save(data)

    revised = [
        {"id": "scene-1", "visual_prompt": "Updated map of Spain", "visual_type": "graphic"},
        {"id": "scene-2", "visual_prompt": "City skyline", "visual_type": "illustration"},
    ]
    saved = studio.save_storyboard(project["id"], revised)
    assert [asset["id"] for asset in saved["asset_records"]] == ["asset-city"]
    assert saved["storyboard"][1]["asset_ids"] == ["asset-city"]


def test_storyboard_rejects_duplicate_scene_ids(studio):
    project = studio.create_project("An example project title")
    with pytest.raises(ValueError, match="unique"):
        studio.save_storyboard(project["id"], [
            {"id": "same", "visual_prompt": "First"},
            {"id": "same", "visual_prompt": "Second"},
        ])


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
    with pytest.raises(TypeError):
        studio.review_video(project["id"], approve=True)


def _authorize(studio, project, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    assert studio.review_video(project["id"])["ready_for_editorial_review"]
    studio.save_youtube_metadata(project["id"], {
        "title": "Verified private test video", "description": "A test upload.", "tags": []})
    return studio.issue_owner_authorization(
        project["id"], owner_confirmed=True, target_account_id="UCtestChannel123")


def _install_fake_youtube(monkeypatch, upload):
    class Uploader:
        def __init__(self, client_secrets_file):
            assert client_secrets_file == "client_secret.json"

        def upload(self, *args, **kwargs):
            return upload(*args, **kwargs)

        def get_channel_id(self):
            return "UCtestChannel123"

    monkeypatch.setitem(sys.modules, "scripts.Uploaders.youtube_uploader",
                        types.SimpleNamespace(YoutubeMediaUploader=Uploader))


def _setup_oauth(studio, monkeypatch, tmp_path):
    secret = tmp_path / "client.json"
    secret.write_text('{"installed":{}}', encoding="utf-8")
    monkeypatch.setattr(studio, "_config", lambda: {"youtube": {"credentials_file": str(secret)}})
    monkeypatch.chdir(tmp_path)


def test_no_publish_without_review(studio, project):
    with pytest.raises(StudioError, match="local Windows console"):
        studio.publish_youtube(project["id"])


def test_invalid_approval_is_rejected(studio, project, monkeypatch):
    _authorize(studio, project, monkeypatch)
    path = studio._dir(project["id"]) / "owner-authorization.json"
    authorization = json.loads(path.read_text(encoding="utf-8"))
    authorization["video_sha256"] = "tampered"
    path.write_text(json.dumps(authorization), encoding="utf-8")
    with pytest.raises(StudioError, match="no longer matches"):
        studio.publish_youtube(project["id"])


def test_render_modification_invalidates_approved_upload(studio, project, monkeypatch):
    _authorize(studio, project, monkeypatch)
    Path(project["video"]).write_bytes(b"tampered")
    with pytest.raises(StudioError, match="no longer matches"):
        studio.publish_youtube(project["id"])


def test_private_only_upload_and_idempotence(studio, project, monkeypatch, tmp_path):
    _authorize(studio, project, monkeypatch)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(return_value={"id": "YT_PRIVATE_123"})
    _install_fake_youtube(monkeypatch, upload)
    result = studio.publish_youtube(project["id"])
    assert result["privacy"] == "private"
    assert result["video_id"] == "YT_PRIVATE_123"
    assert upload.call_args.kwargs["privacy_status"] == "private"
    assert studio._read(project["id"])["status"] == "published"
    second = studio.publish_youtube(project["id"])
    assert second["already_published"] is True
    assert upload.call_count == 1


def test_uncertain_upload_never_auto_retries(studio, project, monkeypatch, tmp_path):
    _authorize(studio, project, monkeypatch)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(side_effect=TimeoutError("Network lost after transfer"))
    _install_fake_youtube(monkeypatch, upload)
    with pytest.raises(TimeoutError):
        studio.publish_youtube(project["id"])
    assert studio._read(project["id"])["status"] == "upload_unknown"
    with pytest.raises(StudioError, match="local Windows console"):
        studio.publish_youtube(project["id"])
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


def test_chatgpt_authored_script_is_persisted_without_python_llm(studio, monkeypatch):
    monkeypatch.setattr(studio, "_chatbot", lambda *_: (_ for _ in ()).throw(AssertionError("LLM called")))
    result = studio.create_script("A legitimate headline", "This is the original narration written by ChatGPT.")
    assert result["script"].startswith("This is the original")
    assert result["schema_version"] == 2


def test_model_callable_review_has_no_approval_switch():
    assert "approve" not in inspect.signature(VideoNewsStudio.review_video).parameters


def test_script_revision_versions_and_invalidates_only_dependent_assets(studio, project):
    saved = studio.save_script(project["id"], "This is replacement narration authored by ChatGPT and longer than thirty characters.")
    assert saved["images"] == []
    assert saved["video"] == ""
    assert saved["versions"][-1]["section"] == "script"


def test_asset_import_is_project_scoped_and_synthetic_disclosure_is_sticky(studio, project):
    from PIL import Image

    studio.save_storyboard(project["id"], [{"id": "scene-1", "visual_prompt": "A newsroom illustration"}])
    inbox = studio.workspace / "_imports"
    inbox.mkdir()
    Image.new("RGB", (64, 64), "navy").save(inbox / "reviewed.png")
    imported = studio.import_asset(project["id"], "reviewed.png", "scene-1", {
        "source": "ChatGPT generated illustration", "license": "owner-reviewed",
        "synthetic_media": True,
    })
    asset = imported["asset"]
    assert Path(asset["path"]).parent == studio._dir(project["id"]) / "images"
    assert len(asset["sha256"]) == 64
    studio.save_youtube_metadata(project["id"], {
        "title": "Synthetic illustration test", "description": "Test", "tags": [],
        "contains_synthetic_media": False,
    })
    assert studio.get_project(project["id"])["youtube_metadata"]["contains_synthetic_media"] is True


def test_asset_import_rejects_paths_outside_staging_inbox(studio, project):
    with pytest.raises(ValueError, match="plain filename"):
        studio.import_asset(project["id"], "..\\.secrets\\token.json", "scene-1", {
            "source": "test", "synthetic_media": False,
        })


def test_async_job_persists_result_and_reuses_idempotency_key(studio, project, monkeypatch):
    finished = threading.Event()

    def fake_generate_voice(project_id, voice):
        finished.set()
        return {"job_id": project_id, "voice": voice}

    monkeypatch.setattr(studio, "generate_voice", fake_generate_voice)
    first = studio.start_job("generate_voice", project["id"], {"voice": "test"},
                             idempotency_key="voice-job-0001")
    assert finished.wait(3)
    deadline = time.monotonic() + 3
    stored = studio.get_job(first["job_id"])
    while stored["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(0.01)
        stored = studio.get_job(first["job_id"])
    assert stored["status"] == "succeeded"
    assert stored["result"]["voice"] == "test"
    second = studio.start_job("generate_voice", project["id"], {"voice": "test"},
                              idempotency_key="voice-job-0001")
    assert second["job_id"] == first["job_id"]


def test_project_listing_suppresses_approval_data(studio, project):
    data = studio._read(project["id"])
    data["approval_digest"] = hashlib.sha256(b"test").hexdigest()
    studio._save(data)
    entries = studio.list_projects()
    assert len(entries) == 1 and entries[0]["id"] == project["id"]
    assert "approval_digest" not in entries[0]
