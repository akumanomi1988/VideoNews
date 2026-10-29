"""Regression coverage for word-timed Edge TTS subtitles, including Spanish accents."""
from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.AI.text_to_speech import TTSEdge


def test_edge_tts_preserves_word_boundary_text_and_timestamps(tmp_path, monkeypatch):
    events = [
        {"type": "audio", "data": b"ID3-test-audio"},
        {"type": "WordBoundary", "offset": 1_000_000, "duration": 3_000_000, "text": "La"},
        {"type": "WordBoundary", "offset": 4_000_000, "duration": 6_000_000, "text": "información"},
        {"type": "WordBoundary", "offset": 10_000_000, "duration": 3_000_000, "text": "está"},
        {"type": "WordBoundary", "offset": 13_000_000, "duration": 6_000_000, "text": "verificada."},
    ]

    class FakeCommunicate:
        def __init__(self, text, voice, **kwargs):
            assert text == "La información está verificada."
            assert voice == "es-ES-ElviraNeural"
            assert kwargs["boundary"] == "WordBoundary"

        async def stream(self):
            for event in events:
                yield event

    monkeypatch.setattr("scripts.AI.text_to_speech.edge_tts.Communicate", FakeCommunicate)
    srt_path = tmp_path / "voice.srt"
    audio_path, error = asyncio.run(TTSEdge(output_dir=str(tmp_path)).text_to_speech(
        "La información está verificada.", voice="es-ES-ElviraNeural", srt_path=str(srt_path)
    ))

    assert error is None
    assert Path(audio_path).read_bytes() == b"ID3-test-audio"
    subtitles = srt_path.read_text(encoding="utf-8")
    assert "información" in subtitles
    assert "está" in subtitles
    assert "00:00:00,100 --> 00:00:00,400" in subtitles
    assert "00:00:00,400 --> 00:00:01,000" in subtitles
    assert subtitles.count("-->") == 4
