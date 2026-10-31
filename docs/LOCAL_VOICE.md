# CPU voice audition on the NewSphere Windows PC

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

## Production boundary

This is a working local voice audition, not a silently activated replacement for
Studio narration. This Kokoro path returns audio without verified word boundaries.
The existing scene/subtitle workflow needs actual word alignment; character-count
timings must not be substituted. Until an alignment integration is implemented and
validated, production keeps its existing TTS path. A preferred voice can be chosen
by listening to the samples before that integration is completed.

Piper is another CPU/Windows option, but is not automatically a quality improvement
over Edge. Its engine and individual voice-model licenses are separate and each
voice model card needs inspection. Larger GPU-oriented speech models have not
been installed merely to provide more options.

## Primary references and licensing

- Runtime, MIT: https://github.com/thewh1teagle/kokoro-onnx
- Model card, Apache-2.0 weights and production use:
  https://huggingface.co/hexgrad/Kokoro-82M
- Spanish voices: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- Piper voices and per-model licensing: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md

No paid image generation, new paid speech API, upload, or voice cloning was used
for these auditions. Preserve applicable notices when redistributing dependencies
or model files; the repository does not commit the runtime or model binaries.
