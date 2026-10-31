"""Isolated CPU synthesis and acoustic forced alignment of a known transcript.

No ASR transcript substitution, proportional timing or implicit provider fallback.
Run with the optional voice runtime, never import its dependencies in Studio.
"""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path


def chunks(text, limit=260):
    """Keep sentence punctuation and bound encoder input to under 30 seconds."""
    sentences = re.split(r"(?<=[.!?;:])\s+", text.strip())
    result = []
    for sentence in sentences:
        words = sentence.split()
        current = []
        for word in words:
            if current and len(" ".join(current + [word])) > limit:
                result.append(" ".join(current))
                current = []
            current.append(word)
        if current:
            result.append(" ".join(current))
    return result


def align_words(model, tokenizer, samples, rate, text):
    import numpy as np
    # Kokoro is 24 kHz; libav performs bandlimited resampling for the encoder.
    import av
    frame = av.AudioFrame.from_ndarray(samples[np.newaxis, :], format="flt", layout="mono")
    frame.sample_rate = rate
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
    frames = resampler.resample(frame) + resampler.resample(None)
    audio = np.concatenate([f.to_ndarray().reshape(-1) for f in frames])
    if len(audio) > 29 * 16000:
        raise RuntimeError("Chunk exceeds the 29-second alignment window; split the narration")
    features = model.feature_extractor(audio)
    aligned = model.find_alignment(tokenizer, [tokenizer.encode(text)], model.encode(features),
                                   min(features.shape[-1], 3000))[0]
    norm = lambda value: "".join(re.findall(r"[^\W_]+", value.casefold()))
    acoustic = [w for w in aligned if norm(w["word"])]
    output, cursor = [], 0
    for original in text.split():
        expected = norm(original)
        if not expected:
            continue
        selected, observed = [], ""
        while cursor < len(acoustic) and len(observed) < len(expected):
            item = acoustic[cursor]
            selected.append(item)
            observed += norm(item["word"])
            cursor += 1
        if observed != expected or not selected:
            raise RuntimeError(f"Alignment transcript mismatch at {original!r}")
        start, end = float(selected[0]["start"]), float(selected[-1]["end"])
        if end <= start or end > len(samples) / rate + .08:
            raise RuntimeError(f"Unresolved acoustic interval at {original!r}")
        output.append({"word": original, "start": start, "end": min(end, len(samples) / rate),
                       "probability": float(np.mean([w["probability"] for w in selected]))})
    if cursor != len(acoustic) or not output:
        raise RuntimeError("Incomplete alignment coverage")
    probabilities = [w["probability"] for w in output]
    if np.mean(probabilities) < .35 or sum(p < .05 for p in probabilities) > max(2, len(output) * .2):
        raise RuntimeError("Low-confidence acoustic alignment; narration needs correction")
    return output


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    h, remainder = divmod(milliseconds, 3600000)
    m, remainder = divmod(remainder, 60000)
    s, ms = divmod(remainder, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
    from faster_whisper.tokenizer import Tokenizer
    from download_local_voice import ASSETS, checksum
    folder = Path(request["output_dir"])
    models = Path(request["model_dir"])
    started = time.perf_counter()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    model_path = models / "kokoro-v1.0.onnx"
    for name, expected in ASSETS.items():
        if checksum(models / name) != expected:
            raise RuntimeError(f"Kokoro model asset failed its pinned checksum: {name}")
    session = ort.InferenceSession(str(model_path), sess_options=options,
                                  providers=["CPUExecutionProvider"])
    engine = Kokoro.from_session(session, str(models / "voices-v1.0.bin"))
    aligner = WhisperModel(request["alignment_model"], device="cpu", compute_type="int8",
                           cpu_threads=4, download_root=str(models / "alignment"),
                           local_files_only=True)
    tokenizer = Tokenizer(aligner.hf_tokenizer, aligner.model.is_multilingual,
                          task="transcribe", language="es")
    loaded = time.perf_counter()
    pieces, words, regions, offset = [], [], [], 0.0
    chunk_dir = folder / "voice_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for index, text in enumerate(chunks(request["text"])):
        key = hashlib.sha256(json.dumps([text, request["voice"], request["speed"],
                                        str(model_path), request["alignment_model"]]).encode()).hexdigest()
        wav = chunk_dir / f"{key}.wav"
        cache = wav.with_suffix(".json")
        if wav.is_file() and cache.is_file():
            cached = json.loads(cache.read_text(encoding="utf-8"))
            if cached["sha256"] != hashlib.sha256(wav.read_bytes()).hexdigest():
                raise RuntimeError("Cached voice chunk checksum mismatch")
            samples, rate = sf.read(wav, dtype="float32")
            local_words = cached["words"]
        else:
            samples, rate = engine.create(text, voice=request["voice"], speed=request["speed"], lang="es")
            samples = np.asarray(samples, dtype=np.float32)
            if not np.isfinite(samples).all() or len(samples) < rate / 10 or np.max(np.abs(samples)) < 1e-5:
                raise RuntimeError(f"Invalid or silent Kokoro output in chunk {index}")
            peak = float(np.max(np.abs(samples)))
            if peak > .98:
                samples *= .98 / peak
            try:
                local_words = align_words(aligner, tokenizer, samples, rate, text)
            except Exception as exc:
                sf.write(folder / "alignment_failed.wav", samples, rate, subtype="PCM_16")
                (folder / "alignment_failure.json").write_text(json.dumps(
                    {"chunk": index, "text": text, "error": str(exc)}, ensure_ascii=False), encoding="utf-8")
                raise
            sf.write(wav, samples, rate, subtype="PCM_16")
            cache.write_text(json.dumps({"words": local_words, "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}), encoding="utf-8")
        for word in local_words:
            words.append(dict(word, start=word["start"] + offset, end=word["end"] + offset))
        regions.append({"text": text, "start": offset, "end": offset + len(samples) / rate})
        pieces.append(samples)
        offset += len(samples) / rate
        # A fixed short sentence gap is real PCM, accounted for in every timestamp.
        pause = np.zeros(round(rate * .12), dtype=np.float32)
        pieces.append(pause)
        offset += len(pause) / rate
    samples = np.concatenate(pieces[:-1])
    previous = 0.0
    for word in words:
        if word["start"] < previous - .001 or word["end"] <= word["start"]:
            raise RuntimeError("Invalid or overlapping acoustic word intervals")
        previous = word["end"]
    sf.write(folder / "narration.wav", samples, rate, subtype="PCM_16")
    srt = "\n".join(f"{i}\n{timestamp(w['start'])} --> {timestamp(w['end'])}\n{w['word']}\n"
                    for i, w in enumerate(words, 1))
    (folder / "word_boundaries.srt").write_text(srt, encoding="utf-8")
    report = {"provider": "kokoro", "voice": request["voice"], "speed": request["speed"],
              "device": "cpu", "sample_rate": rate, "duration_seconds": len(samples) / rate,
              "peak": float(np.max(np.abs(samples))), "word_count": len(words),
              "model_sha256": ASSETS[model_path.name],
              "alignment": "CTranslate2 Whisper cross-attention DTW on known transcript",
              "alignment_model": request["alignment_model"], "alignment_verified": True,
              "model_load_seconds": loaded - started, "total_seconds": time.perf_counter() - started,
              "regions": regions, "words": words}
    (folder / "voice_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
