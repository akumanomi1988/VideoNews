"""Audition optional Kokoro ONNX voices on CPU in an isolated Python environment.

This utility does not publish, replace the production voice, or invent word timings.
"""
import argparse
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path("output/voice_lab/models"))
    parser.add_argument("--voice", choices=("ef_dora", "em_alex", "em_santa"), required=True)
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.threads <= 8:
        parser.error("threads must be from 1 to 8")
    text = args.text_file.read_text(encoding="utf-8").strip()
    if not text or len(text) > 12000:
        parser.error("text must contain 1-12000 characters")
    if args.output.suffix.lower() != ".wav":
        parser.error("output must be a WAV file")
    try:
        import numpy as np
        import onnxruntime as ort
        import soundfile as sf
        from kokoro_onnx import Kokoro
    except ImportError:
        parser.error("Use the isolated runtime created by scripts/setup_local_voice.ps1")

    model = args.model_dir / "kokoro-v1.0.onnx"
    voices = args.model_dir / "voices-v1.0.bin"
    if not model.is_file() or not voices.is_file():
        parser.error("Run setup_local_voice.ps1 to download the official model assets")
    started = time.perf_counter()
    options = ort.SessionOptions()
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    engine = Kokoro.from_session(session, str(voices))
    loaded = time.perf_counter()
    samples, rate = engine.create(text, voice=args.voice, speed=1.0, lang="es")
    finished = time.perf_counter()
    if not np.isfinite(samples).all() or len(samples) < rate / 5 or np.max(np.abs(samples)) < 1e-5:
        raise RuntimeError("Local voice returned invalid or silent audio")
    peak = float(np.max(np.abs(samples)))
    if peak > 0.98:
        samples = samples * (0.98 / peak)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, samples, rate, subtype="PCM_16")
    duration = len(samples) / rate
    report = {"provider": "Kokoro ONNX", "voice": args.voice, "language": "es",
              "providers": session.get_providers(), "threads": args.threads,
              "model_load_seconds": round(loaded - started, 3),
              "synthesis_seconds": round(finished - loaded, 3), "duration_seconds": round(duration, 3),
              "real_time_factor": round((finished - loaded) / duration, 3),
              "sample_rate": rate, "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
              "versions": {name: importlib.metadata.version(name) for name in ("kokoro-onnx", "onnxruntime")},
              "word_alignment": "not supplied by this utility; production synchronization remains unverified"}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
