"""Offline end-to-end render: actual VideoNews orchestration and FFmpeg.

News acquisition, LLM, speech generation and image providers are replaced with
deterministic fixtures. The real NewsVideoProcessor and video assembler must
generate independently playable vertical and horizontal MP4 files.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import subprocess
import sys
import time
import types
import uuid
import wave
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def _stub_module(monkeypatch, name: str, **symbols):
    module = types.ModuleType(name)
    vars(module).update(symbols)
    monkeypatch.setitem(sys.modules, name, module)


class _Aspect(Enum):
    PORTRAIT = (768, 1024)
    LANDSCAPE = (1024, 768)
    SHORTS = (1080, 1920)


class _Preset(Enum):
    NONE = "none"
    REALISM = "realism"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"
    FAUX = "faux"


def _load_real_processor(monkeypatch):
    # Only provider modules are faked. Real orchestration and FFmpeg assembly
    # are deliberately not mocked.
    _stub_module(monkeypatch, "scripts.AI.natural_language_generation", Chatbot=Mock)
    _stub_module(monkeypatch, "scripts.AI.text_to_speech",
                 TTSFactory=Mock, TTSProvider=Enum("TTSProvider", ["EDGE", "ELEVENLABS", "BARK"]))
    _stub_module(monkeypatch, "scripts.AI.text_to_image",
                 FluxImageGenerator=Mock, AspectRatio=_Aspect, StylePreset=_Preset)
    _stub_module(monkeypatch, "scripts.DataFetcher.pexels_media_fetcher",
                 PexelsMediaFetcher=Mock)
    _stub_module(monkeypatch, "scripts.DataFetcher.serpapi_client",
                 SerpAPIProvider=Mock)
    _stub_module(monkeypatch, "scripts.Uploaders.youtube_uploader",
                 YoutubeMediaUploader=Mock)

    monkeypatch.delitem(sys.modules, "news_video_processor", raising=False)
    module = importlib.import_module("news_video_processor")
    return module


def _write_synthetic_audio_and_subtitles(folder: Path):
    audio = folder / "narration.wav"
    with wave.open(str(audio), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\0\0" * 12000)  # 0.75 seconds of valid PCM
    (folder / "subtitles.srt").write_text(
        "1\n00:00:00,000 --> 00:00:00,700\nSample narrated news\n\n",
        encoding="utf-8",
    )
    return str(audio)


@pytest.mark.parametrize("mode,dimensions", [
    ("short", (360, 640)),
    ("long", (640, 360)),
])
@pytest.mark.parametrize("unicode_path", [False, True])
def test_real_ffmpeg_produces_playable_mp4_with_local_export(mode, dimensions, tmp_path, monkeypatch, unicode_path):
    if unicode_path:
        tmp_path = tmp_path / "Proyecto Vídeo News - with spaces"
        tmp_path.mkdir()
    pytest.importorskip("moviepy.editor")
    pytest.importorskip("PIL")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIDEO_UPLOAD_ENABLED", "false")
    monkeypatch.setenv("VIDEO_RENDER_RESOLUTION", "360p")
    monkeypatch.setenv("VIDEO_OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("METRICS_DIR", str(tmp_path / "metrics"))

    from PIL import Image
    visual = tmp_path / "illustration.png"
    Image.new("RGB", (640, 360), (25, 55, 90)).save(visual)
    module = _load_real_processor(monkeypatch)

    from scripts.helpers.media_helper import ImageHelper
    monkeypatch.setattr(ImageHelper, "enhance_thumbnail", lambda *args, **kwargs: None)

    workdir = tmp_path / "job"
    processor = module.NewsVideoProcessor.__new__(module.NewsVideoProcessor)
    processor.temp_dir = str(workdir)
    processor.config = {"video_result": {"background_music": ""}}
    processor.logger = logging.getLogger("offline-test")
    processor.job_id = uuid.uuid4().hex
    processor.job_started_at = time.time()
    processor.cover_path = str(visual)
    processor.image_generator = SimpleNamespace(model="stub")
    fake_article = (
        "A brief factual narration for offline testing.",
        ["one illustrated scene"],
        "Synthetic Test Report",
        "Description of test report",
        ["test", "news"],
        "Synthetic cover",
        "stock illustration",
    )
    processor.article_generator = SimpleNamespace(
        generate_article_and_phrases_short=lambda *_: fake_article,
        generate_article_and_phrases_long=lambda *_: fake_article,
    )
    processor.send_progress = lambda *_: None
    processor.fetch_related_media = lambda *_, **__: [str(visual)]
    processor._generate_and_enhance_thumbnail = lambda *_, **__: None
    processor._synthesize = lambda *_, **__: _write_synthetic_audio_and_subtitles(workdir)

    entry = {"title": "Synthetic news", "description": "Facts for the test."}
    if mode == "short":
        result = processor.process_latest_news_in_short_format(entry)
    else:
        result = processor.process_latest_news_in_long_format(entry)

    assert result is not None, "Real render returned no result; inspect FFmpeg output"
    video = Path(result["local_path"])
    assert video.is_file() and video.stat().st_size > 1000
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", str(video),
    ], capture_output=True, text=True, check=True)
    stream = json.loads(probe.stdout)["streams"][0]
    assert (stream["width"], stream["height"]) == dimensions
    assert list((tmp_path / "metrics").glob("*.json"))
    assert not workdir.exists(), "Successful rendering should clean disposable job assets"
