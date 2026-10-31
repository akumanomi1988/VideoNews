# CPU production narration on the NewSphere Windows PC

The observed machine has an Intel Core i7-2600 (4 cores / 8 threads), 16 GB RAM
and a GTX 660 Ti with 2 GB VRAM. Kokoro ONNX was tested with the explicit
`CPUExecutionProvider`; this evaluation does not use CUDA or the GPU.

## Verified local execution

Runtime: Python 3.11, kokoro-onnx 0.6.1, onnxruntime 1.31.1, four inference
threads. Model: Kokoro v1.0 float32 from the runtime author's official
`model-files-v1.1` release. Model and voices total approximately 354 MB.
Downloads have pinned SHA-256 checksums, and local model cards/license references
are preserved under `output/voice_lab/models/`.

| Voice | Generated audio | Synthesis time | Initial model load |
| --- | ---: | ---: | ---: |
| em_alex | 17.377 s | 18.257 s | 3.352 s |
| ef_dora | 17.009 s | 14.374 s | 4.225 s |

These are observed short-sample timings, not a benchmark of a complete long video.
The generated WAV files were checked with ffprobe. Audition copies are normalized
to the same loudness target for comparison with es-ES-ElviraNeural and
es-ES-AlvaroNeural. Naturalness, accent and expressiveness are subjective and have
not been established by timing measurements. Kokoro's upstream voice list labels
these voices Spanish without promising a specific Spain regional accent.

## Reproduce

From the repository root:

```powershell
.\scripts\setup_local_voice.ps1
.\output\voice_lab\runtime\Scripts\python.exe scripts/local_voice_lab.py --voice em_alex --text-file output/voice_lab/sample_es.txt --output output/voice_lab/kokoro_alex.wav
```

Use an original UTF-8 text file for a different sample. Supported audition voices
are em_alex, ef_dora and em_santa. The runtime lives in the ignored `output/`
directory and uses `requirements.voice.lock.txt`; Studio's NumPy/MoviePy environment
is not upgraded or modified. Setup does not register a service or paid provider.

## Production provider and alignment

New Studio narrations default to Kokoro `em_alex`, speed 1.0, CPU. Set
`TTS_PROVIDER=edge` to explicitly choose the existing network provider. Supported
Kokoro voices are `em_alex`, `ef_dora`, and `em_santa`; the MCP call accepts
`generate_voice(job_id, provider="kokoro", voice="em_alex", speed=1.0)`.
An existing call with an explicit `es-ES-...Neural` voice still selects Edge.
There is no automatic fallback when local speech or alignment fails.

The isolated worker loads Kokoro and multilingual Whisper base once per job.
CTranslate2 runs Whisper in CPU int8 mode. Its `align` operation consumes the
actual generated waveform and **known transcript tokens**, then derives word
intervals from cross-attention using dynamic time warping. It does not substitute
an ASR transcript, or distribute words/characters across the duration. Setup
downloads the alignment model once; production requires local files and does not
download a missing model in the middle of a job.

Natural sentence chunks are bounded to a 29-second encoder window. Real PCM
lengths plus explicit 120 ms gaps determine chunk offsets. Zero-duration words,
transcript mismatches, overlaps, low-confidence regions and silent output fail
the job. `alignment_failure.json` and `alignment_failed.wav` identify a failed
region. Confidence is an acoustic screening heuristic, not proof of semantic
correctness or subjective voice quality. Review names and pronunciation.

Hash-checked `voice_chunks/` preserve completed synthesis/alignment on retry.
The project retains `voice_metadata`; `voice_report.json` includes exact regions,
word intervals, model hash and timings. Outputs are PCM16/24 kHz `narration.wav`,
high-quality `narration.mp3`, and pipeline-compatible `word_boundaries.srt`.
`generate_subtitles` and scene synchronization use the same existing path as Edge.
Render loudness normalization remains in the existing FFmpeg pipeline.

Write numbers and abbreviations as they should be spoken in the authored script.
Do not insert unsupported emotional markup or change approved wording silently.
The separate `local_voice_lab.py` remains an audition-only utility.

Montreal Forced Aligner requires a separate acoustic/dictionary toolchain;
WhisperX adds PyTorch and additional alignment models. Neither was installed.
The chosen CTranslate2 path reuses a moderate multilingual CPU model, works on
the observed i7-2600 without AVX2/GPU, and directly aligns known Spanish text.

Run the optional real test after setup (FFmpeg must be on PATH):
`$env:VIDEONEWS_LIVE_KOKORO='1'; .venv\Scripts\python.exe -m pytest tests/test_kokoro_production.py -q`.
Ordinary regression tests do not install or download optional voice dependencies.

Piper is another CPU/Windows option, but is not automatically a quality improvement
over Edge. Its engine and individual voice-model licenses are separate and each
voice model card needs inspection. Larger GPU-oriented speech models have not
been installed merely to provide more options.

## Primary references and licensing

- Runtime, MIT: https://github.com/thewh1teagle/kokoro-onnx
- Model card, Apache-2.0 weights and production use:
  https://huggingface.co/hexgrad/Kokoro-82M
- Spanish voices: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- CPU runtime/alignment: https://github.com/SYSTRAN/faster-whisper
- CTranslate2 alignment: https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html
- Piper voices and per-model licensing: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md

No paid image generation, new paid speech API, upload, or voice cloning was used
for these auditions. Preserve applicable notices when redistributing dependencies
or model files; the repository does not commit the runtime or model binaries.
