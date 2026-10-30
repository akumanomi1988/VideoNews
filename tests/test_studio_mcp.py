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


def valid_brief(*, privacy="private", status="approved", video_format="short", duration=20):
    url = "https://example.com/story"
    return {
        "selection_mode": "manual",
        "selected_story": {"title": "Verified example headline", "summary": "A sourced account of the event.",
                           "primary_url": url, "why_selected": "Two named sources support the central fact."},
        "alternatives": [{"title": "Alternative story", "primary_url": "https://example.org/other",
                          "reason": "A viable but less timely option."}],
        "verified_sources": [{"title": "Official record", "url": url, "publisher": "Example authority",
                              "published_at": "2026-10-28", "supports": "The record confirms the event."}],
        "format": video_format, "aspect_ratio": "9:16" if video_format == "short" else "16:9",
        "target_duration_seconds": duration, "editorial_angle": "What changed and why it matters.",
        "tone": "Clear and dynamic", "target_audience": "Spanish speaking news viewers",
        "language": "es", "narrative_concept": "Explain the change with evidence and context.",
        "opening_hook": "A concrete verified change has just happened.",
        "visual_strategy": "Scene-matched original graphics and sourced imagery.",
        "image_sources": ["Original local graphics", "Pexels licensed stock"],
        "destination": "NewSphere", "privacy_status": privacy,
        "approval_status": status, "duration_tolerance_seconds": 15,
    }


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
        "aspect_ratio": "9:16",
        "sources": [{"title": "Official record", "url": "https://example.com/story",
                     "publisher": "Example authority", "published_at": "2026-10-28",
                     "summary": "The record confirms the event."}],
        "editorial_brief": valid_brief(), "youtube_metadata": {}, "storyboard": [],
        "asset_records": [],
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


def test_published_project_can_be_reviewed_without_changing_publication(studio, project, monkeypatch):
    project.update(status="published", video_id="existing-video", privacy_status="public")
    studio._save(project)
    before = (studio._dir(project["id"]) / "project.json").read_bytes()
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=1, stdout="", stderr="Invalid controlled fixture"))
    report = studio.review_video(project["id"])
    assert not report["ready_for_editorial_review"]
    assert (studio._dir(project["id"]) / "project.json").read_bytes() == before


def test_draft_is_persisted_atomically_and_no_review_token_leaks(studio, project):
    p = studio.get_project(project["id"])
    assert p["title"] == project["title"]
    assert p["privacy"] == "private"
    assert "approval_digest" not in p
    assert "review_fingerprint" not in p
    assert json.loads((studio._dir(project["id"]) / "project.json").read_text())["id"] == project["id"]


def test_new_projects_default_to_newssphere_cinematic_without_touching_legacy_projects(studio):
    new = studio.create_project("NewSphere visual identity check")
    assert new["visual_profile"] == "NewSphere Cinematic"
    assert new["format"] == "long" and new["aspect_ratio"] == "16:9"
    assert new["production_preferences"]["target_duration_seconds"] == 390
    short = studio.create_project("Explicit short preference override", video_format="short")
    assert short["format"] == "short" and short["aspect_ratio"] == "9:16"
    assert short["production_preferences"]["target_duration_seconds"] == 60
    old = {"id": uuid.uuid4().hex, "title": "Old project", "visual_profile": "legacy preset"}
    studio._save(old)
    assert studio._read(old["id"])["visual_profile"] == "legacy preset"


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
        {"id": "scene-1", "narration": "The first verified scene.", "visual_prompt": "Map of Spain", "visual_type": "graphic"},
        {"id": "scene-2", "narration": "The second verified scene.", "visual_prompt": "City skyline", "visual_type": "illustration"},
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
        {"id": "scene-1", "narration": "The first verified scene.", "visual_prompt": "Updated map of Spain", "visual_type": "graphic"},
        {"id": "scene-2", "narration": "The second verified scene.", "visual_prompt": "City skyline", "visual_type": "illustration"},
    ]
    saved = studio.save_storyboard(project["id"], revised)
    assert [asset["id"] for asset in saved["asset_records"]] == ["asset-city"]
    assert saved["storyboard"][1]["asset_ids"] == ["asset-city"]


def test_storyboard_rejects_duplicate_scene_ids(studio):
    project = studio.create_project("An example project title")
    with pytest.raises(ValueError, match="unique"):
        studio.save_storyboard(project["id"], [
            {"id": "same", "narration": "First sentence.", "visual_prompt": "First scene"},
            {"id": "same", "narration": "Second sentence.", "visual_prompt": "Second scene"},
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


def test_scene_image_durations_follow_tts_word_boundaries(studio, tmp_path):
    boundaries = tmp_path / "word_boundaries.srt"
    words = [
        ("Paraguay", 0.0, 0.5), ("presenta", 0.5, 0.9), ("el", 0.9, 1.0),
        ("proyecto", 1.0, 1.5), ("Yguazú.", 1.5, 2.0),
        ("La", 2.0, 2.2), ("iniciativa", 2.2, 2.9), ("se", 2.9, 3.0),
        ("impulsa", 3.0, 3.5), ("con", 3.5, 3.7), ("Taiwán.", 3.7, 4.0),
    ]
    to_time = lambda value: f"00:00:{int(value):02},{int(round((value % 1) * 1000)):03}"
    boundaries.write_text("\n\n".join(
        f"{index}\n{to_time(start)} --> {to_time(end)}\n{text}"
        for index, (text, start, end) in enumerate(words, 1)
    ) + "\n", encoding="utf-8")
    image_a, image_b = tmp_path / "a.png", tmp_path / "b.png"
    project = {
        "storyboard": [
            {"id": "scene-1", "narration": "Paraguay presenta el proyecto Yguazú."},
            {"id": "scene-2", "narration": "La iniciativa se impulsa con Taiwán."},
        ],
        "narration": [],
        "word_boundaries": str(boundaries),
        "asset_records": [
            {"id": "a", "scene_id": "scene-1", "path": str(image_a)},
            {"id": "b", "scene_id": "scene-2", "path": str(image_b)},
        ],
        "images": [str(image_a), str(image_b)],
    }
    assert studio._scene_image_durations(project, 4.0) == [2.0, 2.0]


def test_generate_subtitles_persists_grouped_caption_path(studio):
    project = studio.create_project("A short subtitle test project")
    studio.save_editorial_brief(project["id"], valid_brief(duration=20))
    studio.save_script(project["id"], "La información pública se encuentra disponible hoy.")
    boundaries = studio._dir(project["id"]) / "word_boundaries.srt"
    boundaries.write_text(
        "1\n00:00:00,000 --> 00:00:00,250\nLa\n\n"
        "2\n00:00:00,250 --> 00:00:00,800\ninformación\n\n"
        "3\n00:00:00,800 --> 00:00:01,100\npública\n\n"
        "4\n00:00:01,100 --> 00:00:01,300\nse\n\n"
        "5\n00:00:01,300 --> 00:00:01,600\nencuentra\n\n"
        "6\n00:00:01,600 --> 00:00:01,800\ndisponible\n\n"
        "7\n00:00:01,800 --> 00:00:02,100\nhoy.\n",
        encoding="utf-8",
    )
    data = studio._read(project["id"])
    data["word_boundaries"] = str(boundaries)
    studio._save(data)

    result = studio.generate_subtitles(project["id"])
    saved = studio.get_project(project["id"])
    assert result["subtitles"] == saved["subtitles"]
    assert Path(saved["subtitles"]).is_file()
    assert saved["word_boundaries"] != saved["subtitles"]
    assert "información" in Path(saved["subtitles"]).read_text(encoding="utf-8")


def test_scene_image_durations_reject_storyboard_text_not_in_script(studio, tmp_path):
    boundaries = tmp_path / "word_boundaries.srt"
    boundaries.write_text("1\n00:00:00,000 --> 00:00:00,500\nBuenos\n\n", encoding="utf-8")
    project = {
        "storyboard": [{"id": "scene-1", "narration": "Texto no pronunciado."}],
        "narration": [], "word_boundaries": str(boundaries),
        "asset_records": [{"id": "a", "scene_id": "scene-1", "path": "a.png"}],
        "images": ["a.png"],
    }
    with pytest.raises(StudioError, match="does not match"):
        studio._scene_image_durations(project, 1.0)


def test_review_without_video_disallows_approval(studio, project):
    data = studio._read(project["id"])
    data["video"] = ""
    studio._save(data)
    report = studio.review_video(project["id"])
    assert not report["ready_for_editorial_review"]
    assert "approval_code" not in report
    with pytest.raises(TypeError):
        studio.review_video(project["id"], approve=True)


def _authorize(studio, project, monkeypatch, privacy_status="private", create_thumbnail=False):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 20.5, "width": 1080, "height": 1920,
        "video_codec": "h264", "audio_codec": "aac", "has_video": True, "has_audio": True})
    brief = dict(project["editorial_brief"])
    brief["privacy_status"] = privacy_status
    studio.save_editorial_brief(project["id"], brief)
    brief["approval_status"] = "approved"
    studio.save_editorial_brief(project["id"], brief)
    studio.save_youtube_metadata(project["id"], {
        "title": "Verified test video", "description": "Source: Example authority.", "tags": []})
    if create_thumbnail:
        from PIL import Image
        Image.new("RGB", (768, 1360), "navy").save(project["images"][0], format="PNG")
        studio.create_thumbnail(project["id"])
    # Upload-policy tests isolate authorization and idempotency. Actual media QA
    # is exercised by the FFmpeg integration suite with real generated fixtures.
    monkeypatch.setattr(studio, "review_video", lambda _job_id: {
        "ready_for_editorial_review": True, "issues": [], "requires_human_fact_check": True})
    assert studio.review_video(project["id"])["ready_for_editorial_review"]
    return studio.issue_owner_authorization(
        project["id"], owner_confirmed=True, target_account_id="UCtestChannel123",
        privacy_status=privacy_status)


def _set_brief_privacy(studio, project, privacy_status):
    brief = dict(project["editorial_brief"])
    brief["privacy_status"] = privacy_status
    studio.save_editorial_brief(project["id"], brief)
    brief["approval_status"] = "approved"
    studio.save_editorial_brief(project["id"], brief)


def _install_fake_youtube(monkeypatch, upload, thumbnail_validation=None):
    class Uploader:
        def __init__(self, client_secrets_file, token_file=None):
            assert Path(client_secrets_file).is_absolute()
            assert Path(token_file).is_absolute()

        def upload(self, *args, **kwargs):
            return upload(*args, **kwargs)

        def get_channel_id(self):
            return "UCtestChannel123"

        def get_channel_info(self):
            return {"id": "UCtestChannel123", "title": "NewSphere"}

        def validate_short_parameters(self, *args, **kwargs):
            return None

        def validate_thumbnail(self, *args, **kwargs):
            if thumbnail_validation is not None:
                thumbnail_validation.append((args, kwargs))
            return None

        def verify_video(self, video_id, expected_channel_id, expected_privacy_status):
            return {"video_id": video_id, "channel_id": expected_channel_id,
                    "privacy_status": expected_privacy_status}

    monkeypatch.setitem(sys.modules, "scripts.Uploaders.youtube_uploader",
                        types.SimpleNamespace(YoutubeMediaUploader=Uploader))


def _setup_oauth(studio, monkeypatch, tmp_path):
    secret = tmp_path / "client.json"
    secret.write_text('{"installed":{}}', encoding="utf-8")
    monkeypatch.setattr(studio, "_config", lambda: {"youtube": {"credentials_file": str(secret)}})
    monkeypatch.chdir(tmp_path)


def test_no_publish_without_review(studio, project, monkeypatch, tmp_path):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    with pytest.raises(StudioError, match="local console"):
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


def test_owner_granted_private_upload_and_idempotence(studio, project, monkeypatch, tmp_path):
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


def test_exact_owner_grant_can_publish_public_once_to_newssphere(
        studio, project, monkeypatch, tmp_path):
    from scripts import publishing_policy
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    studio.save_youtube_metadata(project["id"], {
        "title": "An explicitly approved public test Short",
        "description": "Source-backed report.", "tags": []})
    grant = _authorize(studio, project, monkeypatch, privacy_status="public",
                       create_thumbnail=True)
    assert grant["privacy"] == "public"
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(return_value={"id": "YT_PUBLIC_ONE_USE_1"})
    thumbnail_validation = []
    _install_fake_youtube(monkeypatch, upload, thumbnail_validation)

    result = studio.publish_youtube(project["id"], privacy_status="public")
    assert result["privacy"] == "public"
    assert upload.call_args.kwargs["privacy_status"] == "public"
    assert thumbnail_validation[0][1]["expected_aspect"] == "16:9"
    assert publishing_policy.records()[-1]["outcome"] == "uploaded"
    assert publishing_policy.records()[-1]["privacy_status"] == "public"
    assert studio.publish_youtube(project["id"])['already_published'] is True
    assert upload.call_count == 1


def test_uncertain_upload_never_auto_retries(studio, project, monkeypatch, tmp_path):
    _authorize(studio, project, monkeypatch)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(side_effect=TimeoutError("Network lost after transfer"))
    _install_fake_youtube(monkeypatch, upload)
    with pytest.raises(TimeoutError):
        studio.publish_youtube(project["id"])
    assert studio._read(project["id"])["status"] == "upload_unknown"
    with pytest.raises(StudioError, match="uncertain"):
        studio.publish_youtube(project["id"])
    assert upload.call_count == 1


def test_owner_enrolled_auto_publish_is_private_bounded_and_idempotent(
        studio, project, monkeypatch, tmp_path):
    from scripts import publishing_policy

    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 20.5, "width": 1080, "height": 1920,
        "video_codec": "h264", "audio_codec": "aac", "has_video": True, "has_audio": True})
    _set_brief_privacy(studio, project, "public")
    studio.save_youtube_metadata(project["id"], {
        "title": "A verified private Short", "description": "Source: Example authority. Source-backed report.", "tags": []})
    monkeypatch.setattr(studio, "review_video", lambda _job_id: {
        "ready_for_editorial_review": True, "issues": [], "requires_human_fact_check": True})
    publishing_policy.enroll("UCtestChannel123", 1, privacy_status="public", public_consent=True)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(return_value={"id": "YT_AUTO_PUBLIC_1"})
    _install_fake_youtube(monkeypatch, upload)

    result = studio.publish_youtube(project["id"])
    assert result["privacy"] == "public"
    assert result["youtube_verified"] is True
    assert upload.call_args.kwargs["privacy_status"] == "public"
    assert studio.publish_youtube(project["id"])["already_published"] is True
    assert upload.call_count == 1
    records = publishing_policy.records()
    assert [record["outcome"] for record in records] == ["upload_started", "uploaded"]
    assert all(record["channel_id"] == "UCtestChannel123" for record in records)
    assert all(record["video_sha256"] == studio._hash(Path(project["video"])) for record in records)


def test_auto_publish_unknown_outcome_is_audited_and_never_retried(
        studio, project, monkeypatch, tmp_path):
    from scripts import publishing_policy

    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 20.5, "width": 1080, "height": 1920,
        "video_codec": "h264", "audio_codec": "aac", "has_video": True, "has_audio": True})
    _set_brief_privacy(studio, project, "public")
    studio.save_youtube_metadata(project["id"], {
        "title": "A verified private Short", "description": "Source: Example authority. Source-backed report.", "tags": []})
    monkeypatch.setattr(studio, "review_video", lambda _job_id: {
        "ready_for_editorial_review": True, "issues": [], "requires_human_fact_check": True})
    publishing_policy.enroll("UCtestChannel123", 2, privacy_status="public", public_consent=True)
    _setup_oauth(studio, monkeypatch, tmp_path)
    upload = Mock(side_effect=TimeoutError("Network lost after transfer"))
    _install_fake_youtube(monkeypatch, upload)

    with pytest.raises(TimeoutError):
        studio.publish_youtube(project["id"])
    assert studio._read(project["id"])["status"] == "upload_unknown"
    assert publishing_policy.records()[-1]["outcome"] == "upload_unknown"
    with pytest.raises(StudioError, match="uncertain"):
        studio.publish_youtube(project["id"])
    assert upload.call_count == 1


def test_public_upload_must_be_verified_and_never_retried_on_mismatch(
        studio, project, monkeypatch, tmp_path):
    from scripts import publishing_policy

    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(
        returncode=0, stdout="20.5\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 20.5, "width": 1080, "height": 1920,
        "video_codec": "h264", "audio_codec": "aac", "has_video": True, "has_audio": True})
    _set_brief_privacy(studio, project, "public")
    studio.save_youtube_metadata(project["id"], {
        "title": "A verified NewSphere Short", "description": "Source: Example authority. Source-backed report.", "tags": []})
    monkeypatch.setattr(studio, "review_video", lambda _job_id: {
        "ready_for_editorial_review": True, "issues": [], "requires_human_fact_check": True})
    publishing_policy.enroll("UCtestChannel123", 2, privacy_status="public", public_consent=True)
    _setup_oauth(studio, monkeypatch, tmp_path)

    class Uploader:
        def __init__(self, client_secrets_file, token_file=None):
            pass

        def get_channel_info(self):
            return {"id": "UCtestChannel123", "title": "NewSphere"}

        def validate_short_parameters(self, *args, **kwargs):
            return None

        def validate_thumbnail(self, *args, **kwargs):
            return None

        def upload(self, *args, **kwargs):
            assert kwargs["privacy_status"] == "public"
            return {"id": "YT_PUBLIC_123"}

        def verify_video(self, video_id, channel_id, privacy_status):
            raise RuntimeError("YouTube returned private visibility")

    monkeypatch.setitem(sys.modules, "scripts.Uploaders.youtube_uploader",
                        types.SimpleNamespace(YoutubeMediaUploader=Uploader))
    with pytest.raises(RuntimeError, match="private visibility"):
        studio.publish_youtube(project["id"])
    assert studio._read(project["id"])["status"] == "upload_verification_failed"
    assert studio._read(project["id"])["video_id"] == "YT_PUBLIC_123"
    assert publishing_policy.records()[-1]["outcome"] == "verification_failed"
    with pytest.raises(StudioError, match="reconcile"):
        studio.publish_youtube(project["id"])


def test_model_cannot_expand_owner_enrolled_privacy_status(
        studio, project, monkeypatch, tmp_path):
    from scripts import publishing_policy

    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-policy"))
    publishing_policy.enroll("UCtestChannel123", 2, privacy_status="private")
    with pytest.raises(StudioError, match="not allowed"):
        studio.publish_youtube(project["id"], privacy_status="public")


def test_auto_publish_policy_requires_enrollment(studio, project, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(project["id"]))
    with pytest.raises(StudioError, match="enroll once"):
        studio.publish_youtube(project["id"])


def test_pexels_assets_are_scene_specific_licensed_and_resumable(studio, monkeypatch):
    from io import BytesIO
    from PIL import Image
    import requests

    project = studio.create_project("Pexels storyboard asset proof")
    studio.save_editorial_brief(project["id"], valid_brief())
    studio.save_storyboard(project["id"], [
        {"id": "scene-1", "narration": "A European data center corridor is shown.", "visual_prompt": "A European data center corridor"},
        {"id": "scene-2", "narration": "A scientist reviews AI research.", "visual_prompt": "A scientist reviewing AI research"},
    ])
    monkeypatch.setattr(studio, "_config", lambda: {"pexels": {"api_key": "test-key"}})
    monkeypatch.setattr("scripts.url_safety.validate_public_url", lambda _url: None)
    image = BytesIO()
    Image.new("RGB", (16, 16), "navy").save(image, format="JPEG")
    image_bytes = image.getvalue()
    calls = []

    class Response:
        headers = {"Content-Type": "image/jpeg"}

        def __init__(self, search=False, query=""):
            self.search = search
            self.query = query

        def raise_for_status(self):
            pass

        def json(self):
            return {"photos": [{"url": "https://www.pexels.com/photo/123/",
                                "photographer": "Pexels Photographer",
                                "photographer_url": "https://www.pexels.com/@photo",
                                "src": {"large2x": "https://images.pexels.com/photos/123/photo.jpeg"}}]}

        def iter_content(self, chunk_size):
            return [image_bytes]

    def fake_get(url, **kwargs):
        calls.append(url)
        if "api.pexels.com" in url:
            return Response(search=True)
        return Response()

    monkeypatch.setattr(requests, "get", fake_get)
    first = studio.generate_stock_images(project["id"])
    assert first["provider"] == "Pexels"
    assert len(first["assets"]) == 2
    saved = studio.get_project(project["id"])
    assert [asset["scene_id"] for asset in saved["asset_records"]] == ["scene-1", "scene-2"]
    assert all(asset["provenance"]["license"] == "Pexels License" for asset in saved["asset_records"])
    assert all(asset["synthetic_media"] is False for asset in saved["asset_records"])
    assert len(studio.generate_stock_images(project["id"])["assets"]) == 2
    assert len(calls) == 4


def test_pexels_requires_explicit_selection_in_the_approved_brief(studio, monkeypatch):
    project = studio.create_project("Do not silently use stock")
    brief = valid_brief(status="approved")
    brief["image_sources"] = ["Azure MAI", "Original graphics"]
    studio.save_editorial_brief(project["id"], brief)
    studio.save_storyboard(project["id"], [{"id": "scene-1", "narration": "A supported scene.",
        "visual_prompt": "A specific scene matched illustration"}])
    monkeypatch.setattr(studio, "_config", lambda: {"pexels": {"api_key": "test"}})
    with pytest.raises(StudioError, match="select licensed stock explicitly"):
        studio.generate_stock_images(project["id"])


def test_news_requires_real_search_credentials(studio, monkeypatch):
    monkeypatch.setattr(studio, "_config", lambda: {"serpapi": {"api_key": ""}})
    with pytest.raises(StudioError, match="SERPAPI_API_KEY"):
        studio.research_news("technology news")


def test_news_normalizes_sources_dates_urls_and_duplicates(studio, monkeypatch):
    monkeypatch.setattr(studio, "_config", lambda: {"serpapi": {
        "api_key": "test-only", "use_cache": True, "cache_ttl_hours": 24,
    }})
    from scripts.DataFetcher import serpapi_client
    from scripts.dbControllers import processed_news_controller

    class Provider:
        def __init__(self, **kwargs):
            assert kwargs["api_key"] == "test-only"

        def search_news(self, query, **kwargs):
            assert kwargs["language"] == "es"
            assert kwargs["country"] == "es"
            return [
                {"title": "Paraguay explores AI cooperation", "url": "https://example.com/story",
                 "source": {"name": "DPL News"}, "publishedAt": "10/26/2026, 03:30 PM, +0000 UTC"},
                {"title": "Paraguay explores AI cooperation today", "url": "http://localhost/private",
                 "source": "Example News", "publishedAt": "not a date"},
            ]

    monkeypatch.setattr(serpapi_client, "SerpAPIProvider", Provider)
    monkeypatch.setattr("scripts.url_safety.validate_public_url", lambda url: (
        (_ for _ in ()).throw(ValueError("local URL")) if "localhost" in url else None
    ))
    monkeypatch.setattr(processed_news_controller, "is_url_processed", lambda _url: False)
    result = studio.research_news("Paraguay IA", language="es", limit=5, country="es")

    first, second = result["articles"]
    assert first["source"] == "DPL News"
    assert first["url_validated"] is True
    assert first["published_at_iso"] == "2026-10-26T15:30:00+00:00"
    assert second["source"] == "Example News"
    assert second["url_validated"] is False
    assert second["published_at_iso"] is None
    assert second["duplicate_of"] == "https://example.com/story"


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

    studio.save_storyboard(project["id"], [{"id": "scene-1", "narration": "A newsroom illustration appears.", "visual_prompt": "A newsroom illustration"}])
    inbox = studio.workspace / "_imports"
    inbox.mkdir(exist_ok=True)
    Image.new("RGB", (64, 64), "navy").save(inbox / "reviewed.png")
    imported = studio.import_asset(project["id"], "reviewed.png", "scene-1", {
        "source": "ChatGPT generated illustration", "license": "owner-reviewed",
        "synthetic_media": True,
    })
    asset = imported["asset"]
    assert Path(asset["path"]).parent == studio._dir(project["id"]) / "images"
    assert Path(asset["path"]).suffix == ".png"
    assert asset["mime_type"] == "image/png"
    assert len(asset["sha256"]) == 64
    studio.save_youtube_metadata(project["id"], {
        "title": "Synthetic illustration test", "description": "Test", "tags": [],
        "contains_synthetic_media": False,
    })
    assert studio.get_project(project["id"])["youtube_metadata"]["contains_synthetic_media"] is True


def test_asset_import_order_follows_storyboard_not_upload_order(studio, project):
    from PIL import Image

    studio.save_storyboard(project["id"], [
        {"id": "scene-1", "narration": "The first visual appears.", "visual_prompt": "First visual"},
        {"id": "scene-2", "narration": "The second visual appears.", "visual_prompt": "Second visual"},
    ])
    inbox = studio.workspace / "_imports"
    inbox.mkdir(exist_ok=True)
    Image.new("RGB", (32, 32), "navy").save(inbox / "first.png")
    Image.new("RGB", (32, 32), "gold").save(inbox / "second.png")
    provenance = {"source": "Original test artwork", "synthetic_media": False}
    studio.import_asset(project["id"], "second.png", "scene-2", provenance)
    studio.import_asset(project["id"], "first.png", "scene-1", provenance)

    saved = studio._read(project["id"])
    assert [asset["scene_id"] for asset in saved["asset_records"]] == ["scene-1", "scene-2"]
    assert [scene["asset_ids"][0] for scene in saved["storyboard"]] == [
        asset["id"] for asset in saved["asset_records"]
    ]


def _approved_image_project(studio, title="Cinematic image mapping proof"):
    project = studio.create_project(title)
    brief = valid_brief(status="approved")
    studio.save_editorial_brief(project["id"], brief)
    studio.save_storyboard(project["id"], [
        {"id": "scene-1", "narration": "First supported scene.",
         "visual_prompt": "A distinct cinematic newsroom scene one"},
        {"id": "scene-2", "narration": "Second supported scene.",
         "visual_prompt": "A distinct cinematic newsroom scene two"},
    ])
    return project["id"]


@pytest.mark.parametrize("wrong_ratio", [False, True])
def test_ai_images_map_one_to_each_scene_and_resume_completed_assets(studio, monkeypatch, wrong_ratio):
    from PIL import Image
    from scripts.AI import text_to_image

    job_id = _approved_image_project(studio)
    monkeypatch.setenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "true")
    monkeypatch.setenv("VIDEO_IMAGE_MAX_SCENES_PER_JOB", "12")
    monkeypatch.setattr(studio, "_config", lambda: {"azure_images": {
        "endpoint": "https://example.test/mai/v1/images/generations", "api_key": "unit-test",
        "model": "MAI-test"}})

    class Generator:
        calls = []
        last_generation_info = {"provider": "Azure MAI", "model": "MAI-test", "usage": None}

        def __init__(self, output_dir, **_kwargs):
            self.output_dir = Path(output_dir)

        def preflight(self):
            return {"tls_reachable": True}

        def generate_image(self, prompt, style, ratio):
            self.calls.append((prompt, style, ratio))
            target = self.output_dir / f"fixture-{len(self.calls)}.png"
            Image.new("RGB", (32, 32) if wrong_ratio else (36, 64),
                      (len(self.calls) * 30, 20, 60)).save(target)
            return str(target)

    monkeypatch.setattr(text_to_image, "FluxImageGenerator", Generator)
    if wrong_ratio:
        with pytest.raises(StudioError, match="approved aspect ratio"):
            studio.generate_images(job_id)
        assert studio.get_project(job_id)["asset_records"] == []
        return
    first = studio.generate_images(job_id)
    assert first["generated"] == 2
    saved = studio.get_project(job_id)
    assert [asset["scene_id"] for asset in saved["asset_records"]] == ["scene-1", "scene-2"]
    assert saved["images"] == [asset["path"] for asset in saved["asset_records"]]
    assert [scene["asset_ids"][0] for scene in saved["storyboard"]] == [
        asset["id"] for asset in saved["asset_records"]]
    resumed = studio.generate_images(job_id)
    assert resumed["generated"] == 0 and resumed["resumed"] is True
    assert len(Generator.calls) == 2

    # Recover a partial/out-of-order project without regenerating valid art.
    data = studio._read(job_id)
    data["asset_records"].reverse()
    studio._save(data)
    resumed_again = studio.generate_images(job_id)
    ordered = studio.get_project(job_id)
    assert resumed_again["generated"] == 0
    assert [asset["scene_id"] for asset in ordered["asset_records"]] == ["scene-1", "scene-2"]
    assert len(Generator.calls) == 2


def test_ai_image_partial_failure_persists_success_and_never_falls_back(studio, monkeypatch):
    from PIL import Image
    from scripts.AI import text_to_image

    job_id = _approved_image_project(studio, "Partial AI image recovery proof")
    monkeypatch.setenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "true")
    monkeypatch.setattr(studio, "_config", lambda: {"azure_images": {
        "endpoint": "https://example.test/mai/v1/images/generations", "api_key": "unit-test",
        "model": "MAI-test"}})

    class Generator:
        calls = 0
        last_generation_info = {}

        def __init__(self, output_dir, **_kwargs):
            self.output_dir = Path(output_dir)

        def preflight(self):
            pass

        def generate_image(self, prompt, style, ratio):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("provider unavailable")
            target = self.output_dir / "partial.png"
            Image.new("RGB", (36, 64), "navy").save(target)
            return str(target)

    monkeypatch.setattr(text_to_image, "FluxImageGenerator", Generator)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        studio.generate_images(job_id)
    saved = studio.get_project(job_id)
    assert len(saved["asset_records"]) == 1
    assert saved["asset_records"][0]["scene_id"] == "scene-1"
    assert len(saved["images"]) == 1


def test_ai_image_generation_rejects_scene_count_mismatch_and_disabled_provider(studio, monkeypatch):
    job_id = _approved_image_project(studio)
    monkeypatch.setenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "true")
    with pytest.raises(ValueError, match="storyboard scene count"):
        studio.generate_images(job_id, count=1)
    monkeypatch.setenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "false")
    with pytest.raises(StudioError, match="disabled"):
        studio.generate_images(job_id)


def test_ai_image_generation_loads_runtime_config_before_paid_flag(studio, monkeypatch):
    job_id = _approved_image_project(studio, "First-call runtime configuration regression")
    monkeypatch.setenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "false")
    loaded = []

    def load_config():
        loaded.append(True)
        return {"azure_images": {"endpoint": "", "api_key": ""}}

    monkeypatch.setattr(studio, "_config", load_config)
    with pytest.raises(StudioError, match="disabled"):
        studio.generate_images(job_id)
    assert loaded == [True]


def test_mai_portrait_and_landscape_sizes_stay_within_provider_pixel_limit():
    from scripts.AI.text_to_image import AspectRatio
    for ratio in (AspectRatio.SHORTS, AspectRatio.LANDSCAPE):
        width, height = ratio.value
        assert width >= 768 and height >= 768
        assert width * height <= 1_048_576
    assert abs(AspectRatio.SHORTS.value[0] / AspectRatio.SHORTS.value[1] - 9/16) < 0.001
    assert abs(AspectRatio.LANDSCAPE.value[0] / AspectRatio.LANDSCAPE.value[1] - 16/9) < 0.001


def test_thumbnail_uses_project_visuals_and_validated_spanish_metadata(studio, project):
    from PIL import Image

    image = Path(project["images"][0])
    Image.new("RGB", (300, 500), "navy").save(image)
    studio.save_youtube_metadata(project["id"], {
        "title": "La nueva ley sobre chatbots", "description": "Resumen verificado.",
        "tags": ["tecnología"], "thumbnail_text": "Nueva ley para chatbots",
    })
    result = studio.create_thumbnail(project["id"])
    with Image.open(result["thumbnail"]) as thumbnail:
        assert thumbnail.size == (1280, 720)
        assert thumbnail.format == "JPEG"
    saved = studio.get_project(project["id"])
    assert saved["youtube_metadata"]["thumbnail_path"] == result["thumbnail"]


def test_thumbnail_failure_does_not_hide_successful_video_insert(tmp_path):
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
    from googleapiclient.http import MediaFileUpload

    uploader = YoutubeMediaUploader.__new__(YoutubeMediaUploader)
    uploader.channel_description = ""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"mock video")
    uploader.validate_short_parameters = lambda *args: None
    uploader.validate_thumbnail = lambda *args, **kwargs: None
    uploader.youtube = Mock()
    uploader.youtube.videos.return_value.insert.return_value.execute.return_value = {"id": "private-id"}
    uploader.set_thumbnail = Mock(side_effect=RuntimeError("thumbnail API unavailable"))
    uploader.safe_print = lambda *_args: None
    uploader.handle_error = lambda *_args: None

    result = uploader.upload(str(video), "A valid title", "description", [],
                             thumbnail_path="thumbnail.jpg")
    assert result["id"] == "private-id"
    assert "thumbnail API unavailable" in result["thumbnail_warning"]
    body = uploader.youtube.videos.return_value.insert.call_args.kwargs["body"]
    assert body["snippet"]["defaultLanguage"] == "es"
    assert "defaultAudioLanguage" not in body["snippet"]
    assert body["status"]["privacyStatus"] == "private"


def test_youtube_thumbnail_validation_checks_format_size_and_brief_aspect(tmp_path):
    from PIL import Image
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader

    thumbnail = tmp_path / "thumbnail.jpg"
    Image.new("RGB", (1280, 720), "navy").save(thumbnail, format="JPEG")
    YoutubeMediaUploader.validate_thumbnail(str(thumbnail), expected_aspect="16:9")

    small = tmp_path / "small.png"
    Image.new("RGB", (320, 180), "navy").save(small, format="PNG")
    with pytest.raises(ValueError, match="640 pixels wide"):
        YoutubeMediaUploader.validate_thumbnail(str(small), expected_aspect="16:9")

    wrong_aspect = tmp_path / "wrong.jpg"
    Image.new("RGB", (720, 1280), "navy").save(wrong_aspect, format="JPEG")
    with pytest.raises(ValueError, match="aspect ratio"):
        YoutubeMediaUploader.validate_thumbnail(str(wrong_aspect), expected_aspect="16:9")


@pytest.mark.parametrize("privacy", ["public", "private", "unlisted"])
def test_youtube_readback_verifies_channel_and_privacy(privacy):
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader

    uploader = YoutubeMediaUploader.__new__(YoutubeMediaUploader)
    uploader.youtube = Mock()
    uploader.youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "video-id", "snippet": {"channelId": "UCnewsphere"},
                   "status": {"privacyStatus": privacy}}]
    }
    assert uploader.verify_video("video-id", "UCnewsphere", privacy) == {
        "video_id": "video-id", "channel_id": "UCnewsphere",
        "privacy_status": privacy,
    }


def test_youtube_readback_rejects_wrong_privacy():
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader

    uploader = YoutubeMediaUploader.__new__(YoutubeMediaUploader)
    uploader.youtube = Mock()
    uploader.youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "video-id", "snippet": {"channelId": "UCnewsphere"},
                   "status": {"privacyStatus": "private"}}]
    }
    with pytest.raises(RuntimeError, match="privacy verification"):
        uploader.verify_video("video-id", "UCnewsphere", "public")


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


def test_async_provider_output_does_not_pollute_stdout_mcp_channel(studio, project, capsys, monkeypatch):
    finished = threading.Event()

    def noisy_provider(project_id, voice):
        print("provider progress")
        finished.set()
        return {"job_id": project_id, "voice": voice}

    monkeypatch.setattr(studio, "generate_voice", noisy_provider)
    task = studio.start_job("generate_voice", project["id"], {"voice": "test"})
    assert finished.wait(3)
    deadline = time.monotonic() + 3
    result = studio.get_job(task["job_id"])
    while result["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(0.01)
        result = studio.get_job(task["job_id"])
    captured = capsys.readouterr()
    assert result["status"] == "succeeded"
    assert "provider progress" not in captured.out


def test_project_listing_suppresses_approval_data(studio, project):
    data = studio._read(project["id"])
    data["approval_digest"] = hashlib.sha256(b"test").hexdigest()
    studio._save(data)
    entries = studio.list_projects()
    assert len(entries) == 1 and entries[0]["id"] == project["id"]
    assert "approval_digest" not in entries[0]
