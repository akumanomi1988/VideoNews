# Production acceptance follow-up

The existing public upload `t-im_BO0ES8` remains unchanged. This iteration creates
a local comparison project `075f3f6a397845409d0eec18f852cec1`, derived from
`5ec711d789e543558c5e4bcf626e5452`. It is not uploaded.

## Corrections

- Final encoding uses configurable veryfast/CRF 20 instead of ultrafast/CRF 23.
- QA decodes the full file and measures LUFS, true peak, frame rate, pixel format,
  stream-duration drift and black intervals. It rejects failed decode, silence,
  excessive peaks, incompatible pixel format and prolonged black output.
- Published projects can be reviewed without changing their persisted state.
- Unit tests isolate owner publishing policy and audit storage in temporary directories.
- The locally installed standalone workflow skill was synchronized with the repository:
  Azure image generation is primary; stock requires explicit selection.

## Real artifacts and editorial inspection

Artifacts are under `output/studio/075f3f6a397845409d0eec18f852cec1/`:
`video.mp4`, `thumbnail.jpg`, `qa_contact_sheet.jpg`, `quality_acceptance.json`.
The previous seven-scene contact sheet showed a cartoon-like second scene among
photorealistic illustrations. Only that scene was regenerated with Azure MAI;
the six retained image checksums were verified unchanged. The new image uses
photographic rendering and retains synthetic-media provenance. No Pexels was used.
The Spanish narration, factual qualifications and timed subtitles were reused.

The original and final comparison encode measured 1080x1920, 24 FPS, yuv420p,
67.625 seconds, -16.5 LUFS, -4.5 dBTP and approximately 12 ms stream-duration
drift, with no detected black intervals. The final revised encode is 7,925,367
bytes. Its contact sheet was inspected after the second-scene replacement:
the previous cartoon mismatch is resolved and captions remain legible at the
sampled points. These are technical measurements and sampled visual inspection, not a
claim that subjective cinematic quality or factual truth can be automated.

No licensed music file is configured, so this production has no background music.
No new speech synthesis was needed. No claim of a new listening comparison is made.
Provider usage is recorded on the regenerated asset; no monetary price is inferred.

## Connection and publication boundaries

The active host's actual MCP `studio_status` and `get_project` calls succeeded.
The subsequent active `review_video` request did not return within the diagnostic
wait and was abandoned; that host connection is not counted as a successful new
QA call. New-process local QA and the real stdio protocol tests exercise the
updated code. Reload the host MCP connection to load the new Python modules.
No additional public upload is authorized or performed by this follow-up.

The final Windows regression run passed 371 tests, skipped one, and emitted two
dependency warnings. Tests include real FFmpeg portrait/landscape rendering and
new real-media acceptance/negative cases; external provider calls are not implied
by those fixture tests. The separate Azure regeneration above was real.
