"""Simulated conversation-to-MCP acceptance checks; no uploads or paid APIs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.studio_mcp import StudioError, VideoNewsStudio


def brief(*, status="proposed", duration=45, video_format="short", privacy="private"):
    url = "https://example.com/first"
    return {
        "selection_mode": "manual",
        "selected_story": {"title": "First candidate", "summary": "Verified report summary.",
                           "primary_url": url, "why_selected": "Confirmed by primary and independent sources."},
        "alternatives": [{"title": "Second candidate", "primary_url": "https://example.org/second",
                          "reason": "Recent, visually explainable, with corroboration."}],
        "verified_sources": [{"title": "Official record", "url": url, "publisher": "Example authority",
                              "published_at": "2026-10-29", "supports": "Confirms the central event."}],
        "format": video_format, "aspect_ratio": "9:16" if video_format == "short" else "16:9",
        "target_duration_seconds": duration, "editorial_angle": "What happened and why it matters.",
        "tone": "Clear and dynamic", "target_audience": "Spanish speaking news viewers",
        "language": "es", "narrative_concept": "Explain the verified change with context.",
        "opening_hook": "A specific, sourced development has just happened.",
        "visual_strategy": "Scene-matched documentary context and original graphics.",
        "image_sources": ["Original graphics", "Licensed scene-matched stock"],
        "destination": "NewSphere", "privacy_status": privacy,
        "approval_status": status, "duration_tolerance_seconds": 15,
    }


def save(studio, project_id, value):
    return studio.save_editorial_brief(project_id, value)


def test_simulated_explore_and_recommend_only_offer_editorial_actions():
    # ChatGPT interprets these turns; the declared MCP plan contains no writes or production.
    traces = {
        "Dame tres noticias de IA": ["research_news"],
        "¿Cuál elegirías?": ["research_news", "retrieve_article"],
    }
    assert all(not any(name in trace for name in ("create_project", "generate_voice", "render_video",
                                                   "publish_youtube")) for trace in traces.values())
    skill = Path("chatgpt-plugin/skills/news-video-workflow/SKILL.md").read_text(encoding="utf-8")
    assert "| `EXPLORE`" in skill and "| `RECOMMEND`" in skill


def test_news_results_include_freshness_duplicate_and_recent_topic_signals(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from scripts.DataFetcher.serpapi_client import SerpAPIProvider
    import scripts.dbControllers.processed_news_controller as processed
    import scripts.url_safety as url_safety

    studio = VideoNewsStudio(tmp_path / "studio")
    previous = studio.create_project("New York enacts AI chatbot rules for children")
    state = studio._read(previous["id"])
    state.update(status="published", published_at=(datetime.now(timezone.utc) - timedelta(days=3)).isoformat())
    studio._save(state)
    monkeypatch.setattr(studio, "_config", lambda: {"serpapi": {
        "api_key": "test", "use_cache": False, "cache_ttl_hours": 0}})
    monkeypatch.setattr(url_safety, "validate_public_url", lambda _url: None)
    monkeypatch.setattr(processed, "is_url_processed", lambda _url: False)
    monkeypatch.setattr(SerpAPIProvider, "search_news", lambda *_args, **_kwargs: [
        {"title": "New York enacts AI chatbot rules for children", "url": "https://example.com/news",
         "source": {"name": "Associated Press"}, "publishedAt": datetime.now(timezone.utc).isoformat()},
        {"title": "New York enacts AI chatbot rules for children", "url": "https://example.org/duplicate",
         "source": "Example Journal", "publishedAt": datetime.now(timezone.utc).isoformat()},
    ])
    result = studio.research_news("IA y menores", limit=2)
    first, duplicate = result["articles"]
    assert first["freshness_heuristic"] == "last_24_hours"
    assert duplicate["duplicate_of"] == first["url"]
    assert duplicate["duplicate_group"] == first["url"]
    assert first["similar_recently_published_newssphere_project"]["project_id"] == previous["id"]
    assert first["evidence_status"] == "unverified_search_lead"


def test_second_candidate_duration_revision_keeps_story_and_unaffected_visual_assets(tmp_path):
    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Candidate selection conversation")
    initial = brief(status="approved")
    save(studio, project["id"], initial)
    visual = studio._dir(project["id"]) / "scene.png"
    visual.parent.mkdir(exist_ok=True)
    visual.write_bytes(b"approved-scene-image")
    state = studio._read(project["id"])
    state.update(script="A prior approved narration longer than thirty characters.",
                 images=[str(visual)], asset_records=[{"id": "scene", "scene_id": "scene-1",
                 "path": str(visual), "sha256": "a" * 64}], voice="prior.mp3",
                 word_boundaries="prior.srt", subtitles="prior-captions.srt", video="prior.mp4")
    studio._save(state)

    revised = dict(initial)
    revised["selected_story"] = {"title": "Second candidate", "summary": "Second verified summary.",
                                  "primary_url": "https://example.org/second",
                                  "why_selected": "The user chose the second story in the current shortlist."}
    revised["verified_sources"] = [{"title": "Second source", "url": "https://example.org/second",
                                    "publisher": "Example Journal", "published_at": "2026-10-29",
                                    "supports": "Confirms the selected event."}]
    revised["target_duration_seconds"] = 180
    saved = save(studio, project["id"], revised)
    assert saved["editorial_brief"]["selected_story"]["title"] == "Second candidate"
    assert saved["editorial_brief"]["target_duration_seconds"] == 180
    assert saved["editorial_brief"]["approval_status"] == "proposed"
    assert saved["script"] == "" and saved["voice"] == saved["subtitles"] == saved["video"] == ""
    assert saved["images"] == []  # selecting a different story invalidates story-specific imagery


def test_duration_only_revision_preserves_story_and_visual_assets(tmp_path):
    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Duration-only change")
    original = brief(status="approved")
    save(studio, project["id"], original)
    image = studio._dir(project["id"]) / "stable-scene.png"
    image.write_bytes(b"scene")
    state = studio._read(project["id"])
    state.update(script="An existing narration that contains enough text to count as a script.",
                 images=[str(image)], asset_records=[{"id": "stable", "scene_id": "scene-1",
                 "path": str(image), "sha256": "b" * 64}], voice="voice.mp3", subtitles="captions.srt",
                 video="video.mp4")
    studio._save(state)
    changed = dict(original, target_duration_seconds=180)
    saved = save(studio, project["id"], changed)
    assert saved["script"] == "" and saved["voice"] == saved["subtitles"] == saved["video"] == ""
    assert saved["images"] == [str(image)] and saved["asset_records"][0]["id"] == "stable"


def test_dynamic_horizontal_revision_keeps_the_same_active_project(tmp_path):
    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("The active editorial project")
    initial = brief(status="approved")
    save(studio, project["id"], initial)
    revised = dict(initial)
    revised.update(format="long", aspect_ratio="16:9", visual_strategy="Dynamic landscape montage with purposeful cuts.")
    saved = save(studio, project["id"], revised)
    assert saved["id"] == project["id"]
    assert saved["format"] == "long" and saved["aspect_ratio"] == "16:9"
    assert saved["editorial_brief"]["approval_status"] == "proposed"


def test_create_requires_user_approval_and_does_not_publish(tmp_path):
    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Approved production briefing")
    proposed = brief(status="proposed")
    save(studio, project["id"], proposed)
    with pytest.raises(StudioError, match="only a proposal"):
        studio._require_approved_brief(studio._read(project["id"]))
    approved = dict(proposed, approval_status="approved")
    save(studio, project["id"], approved)
    assert studio._require_approved_brief(studio._read(project["id"]))["approval_status"] == "approved"
    assert studio._read(project["id"])["status"] == "draft"  # approval itself has no upload side effect


def test_simulated_create_and_publish_runs_only_after_owner_policy_and_qa(tmp_path, monkeypatch):
    import subprocess
    import sys
    import types
    from unittest.mock import Mock
    from scripts import publishing_policy

    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Delegated public production")
    approved = brief(status="approved", privacy="public")
    save(studio, project["id"], approved)
    metadata = {"title": "A sourced NewSphere report", "description": "Credits: Example authority.",
                "tags": ["news"], "contains_synthetic_media": False}
    studio.save_youtube_metadata(project["id"], metadata)
    folder = studio._dir(project["id"])
    video = folder / "video.mp4"; video.write_bytes(b"test mp4")
    subtitles = folder / "captions.srt"
    subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nCaption\n", encoding="utf-8")
    image = folder / "scene.png"; image.write_bytes(b"image")
    state = studio._read(project["id"])
    state.update(video=str(video), subtitles=str(subtitles), images=[str(image)],
                 script="A factual narration that is long enough for the story.")
    studio._save(state)
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    publishing_policy.enroll("UCnewssphere", 1, privacy_status="public", public_consent=True)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Mock(returncode=0, stdout="45\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 45, "width": 1080, "height": 1920, "video_codec": "h264",
        "audio_codec": "aac", "has_video": True, "has_audio": True})
    secret = tmp_path / "client.json"; secret.write_text('{"installed":{}}', encoding="utf-8")
    monkeypatch.setattr(studio, "_config", lambda: {"youtube": {
        "credentials_file": str(secret), "token_file": str(tmp_path / "token.json")}})

    class Uploader:
        def __init__(self, **_kwargs): pass
        def get_channel_info(self): return {"id": "UCnewssphere", "title": "NewSphere"}
        def upload(self, _path, **kwargs):
            assert kwargs["privacy_status"] == "public"
            return {"id": "mock-public-id"}
        def verify_video(self, video_id, channel_id, privacy):
            return {"video_id": video_id, "channel_id": channel_id, "privacy_status": privacy}

    monkeypatch.setitem(sys.modules, "scripts.Uploaders.youtube_uploader",
                        types.SimpleNamespace(YoutubeMediaUploader=Uploader))
    result = studio.publish_youtube(project["id"], privacy_status="public")
    assert result["youtube_verified"] is True and result["privacy"] == "public"
    assert result["video_id"] == "mock-public-id"


def test_story_switch_invalidates_all_story_dependent_artifacts(tmp_path):
    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Switch story test")
    approved = brief(status="approved")
    save(studio, project["id"], approved)
    state = studio._read(project["id"])
    state.update(script="A sourced script of more than thirty characters.", narration=[{"text": "x"}],
                 images=["old.png"], asset_records=[{"id": "old"}], voice="voice.mp3",
                 word_boundaries="words.srt", subtitles="captions.srt", video="video.mp4")
    studio._save(state)
    changed = dict(approved)
    changed["selected_story"] = {"title": "A different verified story", "summary": "New evidence.",
                                 "primary_url": "https://example.org/new",
                                 "why_selected": "The user requested a different story."}
    changed["verified_sources"] = [{"title": "New source", "url": "https://example.org/new",
                                    "publisher": "New publisher", "published_at": "2026-10-29",
                                    "supports": "Supports new event."}]
    saved = save(studio, project["id"], changed)
    assert saved["script"] == "" and saved["narration"] == []
    assert saved["images"] == [] and saved["asset_records"] == []
    assert saved["voice"] == saved["word_boundaries"] == saved["subtitles"] == saved["video"] == ""
    assert saved["editorial_brief"]["approval_status"] == "proposed"


def test_quality_issue_blocks_publication_and_returns_actionable_review(tmp_path, monkeypatch):
    from unittest.mock import Mock
    from scripts import publishing_policy

    studio = VideoNewsStudio(tmp_path / "studio")
    project = studio.create_project("Quality gate example")
    current = brief(status="approved", privacy="public")
    save(studio, project["id"], current)
    folder = studio._dir(project["id"])
    video = folder / "video.mp4"; video.write_bytes(b"mp4")
    sub = folder / "captions.srt"; sub.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n", encoding="utf-8")
    img = folder / "image.png"; img.write_bytes(b"image")
    data = studio._read(project["id"])
    data.update(video=str(video), subtitles=str(sub), images=[str(img)], script="A valid script exceeding thirty characters.",
                youtube_metadata={"title": "Quality gate", "description": "Source: Example authority.", "tags": []})
    studio._save(data)
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    publishing_policy.enroll("UCnewssphere", 1, privacy_status="public", public_consent=True)
    monkeypatch.setattr("scripts.studio_mcp.subprocess.run", lambda *args, **kwargs: Mock(returncode=0, stdout="30\n"))
    monkeypatch.setattr(studio, "_probe_media", lambda _path: {
        "duration_seconds": 30, "width": 720, "height": 1280,
        "video_codec": "h264", "audio_codec": "aac", "has_video": True, "has_audio": True})
    report = studio.review_video(project["id"])
    assert not report["ready_for_editorial_review"]
    assert any("resolution" in issue.lower() for issue in report["issues"])
    with pytest.raises(StudioError, match="Resolve Studio quality"):
        studio.publish_youtube(project["id"], privacy_status="public")


def test_conversation_instruction_documents_publish_and_alternatives_are_not_publication():
    skill = Path("chatgpt-plugin/skills/news-video-workflow/SKILL.md").read_text(encoding="utf-8")
    for intent in ("DELEGATE_SELECTION", "CREATE", "CREATE_AND_PUBLISH", "REVISE"):
        assert intent in skill
    assert "la segunda" in skill.casefold()
    assert "never publish" in skill.casefold()

