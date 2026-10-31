"""Production TTS dispatch without loading optional local models into Studio."""
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def kokoro_status(config):
    settings = config["tts_kokoro"]
    runtime = ROOT / settings["python"]
    models = ROOT / settings["model_dir"]
    alignment = models / "alignment" / ("models--Systran--faster-whisper-" + settings["alignment_model"]) / "snapshots"
    aligned_model_present = alignment.is_dir() and any(
        all((snapshot / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json"))
        for snapshot in alignment.iterdir())
    ready = runtime.is_file() and all((models / n).is_file() for n in ("kokoro-v1.0.onnx", "voices-v1.0.bin"))
    return {"available": ready, "model": "kokoro-v1.0.onnx", "voice": settings["voice"],
            "device": "cpu", "alignment_model": settings["alignment_model"],
            "alignment_model_present": aligned_model_present,
            "ready_for_live_test": ready and aligned_model_present,
            "verification": "Presence check only; see project voice_report.json for live alignment evidence"}


def synthesize(text, folder, config, provider=None, voice=None, speed=None):
    # An explicit historic Edge voice retains its old meaning.
    provider = provider or ("edge" if voice and voice.endswith("Neural") else config["tts"]["provider"])
    if provider not in ("edge", "kokoro"):
        raise ValueError("Studio TTS provider must be edge or kokoro")
    folder = Path(folder)
    if provider == "edge":
        from scripts.AI.text_to_speech import TTSEdge
        voice = voice or config["tts_edge"]["voice"]
        if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+Neural", voice):
            raise ValueError("Invalid Edge TTS voice name")
        TTSEdge(output_dir=str(folder)).text_to_speech_file(text, language=voice[:2], voice=voice,
            output_path=str(folder / "narration.mp3"), srt_path=str(folder / "word_boundaries.srt"))
        return {"provider": provider, "voice": voice, "alignment": "Edge word boundary events"}
    settings = config["tts_kokoro"]
    voice = voice or settings["voice"]
    speed = float(speed if speed is not None else settings["speed"])
    if voice not in ("em_alex", "ef_dora", "em_santa") or not .75 <= speed <= 1.25:
        raise ValueError("Kokoro requires a supported Spanish voice and speed 0.75-1.25")
    if settings["device"] != "cpu":
        raise ValueError("This Kokoro production runtime supports CPU only")
    if not kokoro_status(config)["ready_for_live_test"]:
        raise RuntimeError("Kokoro runtime/model/alignment unavailable; run setup_local_voice.ps1")
    request = folder / "voice_request.json"
    request.write_text(json.dumps({"text": text, "voice": voice, "speed": speed,
        "output_dir": str(folder.resolve()), "model_dir": str((ROOT / settings["model_dir"]).resolve()),
        "alignment_model": settings["alignment_model"]}, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([str(ROOT / settings["python"]), str(ROOT / "scripts/kokoro_worker.py"),
                              "--request", str(request.resolve())], capture_output=True,
                              stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", timeout=3600)
    if result.returncode:
        raise RuntimeError("Kokoro synthesis/alignment failed: " + result.stderr[-1800:])
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(folder / "narration.wav"),
                    "-codec:a", "libmp3lame", "-q:a", "2", str(folder / "narration.mp3")],
                    stdin=subprocess.DEVNULL, check=True, capture_output=True, timeout=120)
    return json.loads((folder / "voice_report.json").read_text(encoding="utf-8"))
