"""Provider safety and optional real CPU production acceptance tests."""
import copy
import json
import os
import wave
from pathlib import Path

import pytest

from scripts.kokoro_worker import chunks
from scripts.runtime_config import DEFAULTS
from scripts.tts_service import synthesize, kokoro_status, ROOT


def test_natural_chunking_preserves_transcript_and_encoder_bound():
    text = "¿Qué ocurre? " + " ".join(["La investigación continúa, con datos contrastados."] * 20)
    result = chunks(text)
    assert " ".join(result) == text
    assert all(len(part) <= 260 for part in result)
    assert result[0] == "¿Qué ocurre?"


@pytest.mark.parametrize("provider,voice,speed", [
    ("unknown", None, None), ("kokoro", "unknown", 1), ("kokoro", "em_alex", 0),
])
def test_invalid_provider_options_fail_before_external_work(tmp_path, provider, voice, speed):
    with pytest.raises(ValueError):
        synthesize("A test", tmp_path, copy.deepcopy(DEFAULTS), provider, voice, speed)
    assert not list(tmp_path.iterdir())


def test_missing_kokoro_model_never_falls_back_to_edge(tmp_path, monkeypatch):
    config = copy.deepcopy(DEFAULTS)
    config["tts_kokoro"]["model_dir"] = str(tmp_path / "missing")
    import scripts.AI.text_to_speech as edge
    monkeypatch.setattr(edge, "TTSEdge", lambda **kw: pytest.fail("Unexpected paid/network fallback"))
    assert not kokoro_status(config)["ready_for_live_test"]
    with pytest.raises(RuntimeError, match="unavailable"):
        synthesize("Narración sin modelo", tmp_path, config, provider="kokoro")


def test_explicit_historic_edge_voice_keeps_provider(tmp_path, monkeypatch):
    import scripts.AI.text_to_speech as edge
    called = []
    class ExistingEdge:
        def __init__(self, **kwargs):
            pass
        def text_to_speech_file(self, *args, **kwargs):
            called.append(kwargs)
    monkeypatch.setattr(edge, "TTSEdge", ExistingEdge)
    report = synthesize("Texto anterior", tmp_path, copy.deepcopy(DEFAULTS), voice="es-ES-ElviraNeural")
    assert report["provider"] == "edge"
    assert called[0]["voice"] == "es-ES-ElviraNeural"


def test_failed_worker_is_reported_without_provider_fallback(tmp_path, monkeypatch):
    import scripts.tts_service as service
    from types import SimpleNamespace
    monkeypatch.setattr(service, "kokoro_status", lambda config: {"ready_for_live_test": True})
    monkeypatch.setattr(service.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stderr="Unresolved acoustic interval"))
    with pytest.raises(RuntimeError, match="Unresolved acoustic interval"):
        synthesize("Texto conocido", tmp_path, copy.deepcopy(DEFAULTS), provider="kokoro")
    assert not (tmp_path / "narration.mp3").exists()


@pytest.mark.skipif(os.getenv("VIDEONEWS_LIVE_KOKORO") != "1", reason="Explicit optional CPU runtime test")
def test_live_kokoro_and_known_transcript_acoustic_alignment(tmp_path):
    text = (ROOT / "examples/voice_audition_es.txt").read_text(encoding="utf-8").strip()
    report = synthesize(text, tmp_path, copy.deepcopy(DEFAULTS), provider="kokoro", voice="em_alex")
    assert report["alignment_verified"] and report["device"] == "cpu"
    assert report["peak"] <= .981
    assert " ".join(w["word"] for w in report["words"]) == text
    previous = 0
    for word in report["words"]:
        assert previous <= word["start"] < word["end"] <= report["duration_seconds"]
        previous = word["end"]
    with wave.open(str(tmp_path / "narration.wav")) as audio:
        assert audio.getframerate() == 24000 and audio.getsampwidth() == 2
        assert abs(audio.getnframes() / audio.getframerate() - report["duration_seconds"]) < .001
    # A second run must retain valid PCM chunks instead of paying synthesis time again.
    hashes = {p.name: p.stat().st_mtime_ns for p in (tmp_path / "voice_chunks").glob("*.wav")}
    synthesize(text, tmp_path, copy.deepcopy(DEFAULTS), provider="kokoro", voice="em_alex")
    assert hashes == {p.name: p.stat().st_mtime_ns for p in (tmp_path / "voice_chunks").glob("*.wav")}
