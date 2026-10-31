# Kokoro CPU production acceptance — 31 October 2026

## Observed public production

- Project: `a32e5c2505fc454d96c3f734f3b3a469`.
- Video: https://www.youtube.com/watch?v=PmKn80yYplk
- Title: **Lucy llega a los troyanos: un viaje al origen de los planetas**.
- Channel: NewSphere, `UCXX3S1RI4iahIcbsOl_m3gw`.
- YouTube API confirmed `privacyStatus=public`, `processingStatus=succeeded`,
  H.264, 1920x1080, 24 FPS, `PT3M40S`, Spanish language and audio language,
  approved title/description/tags and a custom 1280x720 thumbnail.
- Final API publication timestamp: `2026-10-31T15:01:30Z`.
- Exactly one audited insert attempt, followed by `uploaded`. Repeated official
  publication calls returned `already_published` with the same ID and no new audit
  entry. A fresh process and the chat's actual `get_project` MCP call recovered
  the published state, video ID and `kokoro / em_alex` voice metadata.
- MP4 SHA-256: `c8c8ada24033a88ec20d540f42086523727cbd0724c388829366f42c99aaafc1`.

This was the one new public video expressly authorized for this integration.
No other project was published, and the owner policy was not expanded or edited.
The existing policy remained channel-bound, public, with a daily limit of 100.

## Actual speech and media

The observed Windows machine uses an i7-2600, 16 GB RAM, Python 3.11 and CPU
inference. Studio's NumPy 1.26 environment remains separate from the optional
Kokoro runtime (Kokoro ONNX 0.6.1, ONNX Runtime 1.31.1, faster-whisper 1.2.1,
CTranslate2 4.8.4). No GPU inference or paid speech API was used.

Kokoro `em_alex`, speed 1.0, produced **219.9447 seconds** of PCM16/24 kHz speech:
576 words, peak amplitude 0.7151. Cold synthesis plus alignment took 312.589
seconds, including 4.650 seconds to load models; combined real-time factor 1.42.
Other acceptance work ran concurrently, so this is an observed run rather than
an isolated hardware benchmark. Completed chunks are retained for retries.

The final MP4 is **219.9583 seconds**, landscape 16:9, 1920x1080, H.264/yuv420p,
24 FPS with AAC audio. Full FFmpeg decode found no errors or unexpected black
intervals. Audio/video duration drift was 20.3 ms, integrated loudness -17.2 LUFS,
and true peak -4.4 dBTP.

Twelve original Azure MAI landscape images (1360x768) were generated, within the
configured twelve-image cap. Twelve original source-grounded explanatory graphics
provide 24 narrative beats. No Pexels or stock fallback was used. Scene order,
checksums, orientation and acoustic word-based timing were checked. The contact
sheet and thumbnail were visually inspected. AI art is illustrative, has the
small IA marker, and is disclosed in the description and upload request.
Azure returned token usage; no verifiable dollar charge was returned, so no cost
is invented. Music is absent because no licensed track was selected.

## Editorial and acoustic verification limits

The announcement concerns arrival in the Trojan **region**, not an already
completed close flyby. The first Trojan encounter remains scheduled for August
2027. Sources were retrieved and compared against each narration paragraph:

- [NASA announcement, 28 October 2026](https://science.nasa.gov/blogs/lucy/2026/10/28/nasas-lucy-reaches-trojan-asteroid-region-5-years-after-launch/)
- [NASA science objectives](https://science.nasa.gov/mission/lucy/science/)
- [NASA mission FAQ](https://science.nasa.gov/mission/lucy/frequently-asked-questions/)
- [NASA trajectory visualization, 27 October 2026](https://svs.gsfc.nasa.gov/5686/)

Known-text cross-attention/DTW alignment used the actual PCM waveform. No word or
character proportional timings were generated. Independent full-audio ASR took
48.06 seconds and had 0.933 token similarity before number normalization; its
differences include spelling, spoken-number formatting and date recognition.
Date-token contrast on the same waveform supported the intended 2027/2028/2033
word sequences over erroneous ASR alternatives. This is acoustic evidence, not
human listening. Subjective expressiveness and a specific Spain regional accent
are not certified. Matched-loudness Kokoro/Edge samples remain for owner comparison.
Structural QA never marks semantic review as automatically proven.

## Corrections demonstrated by the E2E

- Provider dispatch, explicit voice/speed selection, isolated CPU worker and
  actual acoustic alignment; no implicit Edge fallback.
- Natural bounded sentence chunks, exact PCM offsets, short real pauses,
  confidence/interval validation, partial-result caching and pinned Kokoro hashes.
- Long voice jobs re-read the active project before saving, preserving unrelated
  assets persisted during synthesis and rejecting changed scripts.
- QA accepts original imported graphics with the documented source provenance
  contract, while still rejecting missing provenance and placeholders.
- Optional selected-scene/framed thumbnail composition keeps the subject visible
  above the text card and verifies the source asset checksum.
- Windows MCP startup initializes existing NumPy/Pillow DLL dependencies before
  starting stdio readers. A live hung process was inspected before repair.
- FFmpeg QA/render processes disable stdin interaction; QA and speech subprocesses
  receive `DEVNULL` stdin. A second live pre-upload hang was traced to FFmpeg's
  inherited MCP stdin. Both blocked attempts occurred **before** an upload audit
  record or insert. After repair the official MCP publishing call completed.

## MCP and plugin evidence

The packaged launcher was initialized over real stdio JSON-RPC. Tool discovery
exposed `provider`, `voice`, and `speed`; `studio_status` reported Kokoro readiness.
An asynchronous `generate_voice` call generated real Kokoro audio and aligned
words in a separate acceptance project. The public production was reviewed and
published through `publish_youtube` over a fresh MCP connection, without bypassing
Studio policy/QA. The already-loaded chat connection then read the published
project successfully.

The existing private plugin identity was preserved and its 0.3.11 release was
uploaded and read back. The installed standalone workflow skill was synchronized.
Already-running hosts retain their old tool catalog until they reload their MCP
connection; the previous catalog does not expose the new optional voice arguments.
A separate ChatGPT Desktop UI session was not exercised. Windows MCP SDK client
cleanup emitted a Proactor closed-pipe warning after successful calls; this did
not change the persisted jobs or upload outcome.

## Local evidence paths

All following paths are relative to the repository and remain ignored local
artifacts rather than Git binaries:

| Artifact | Path |
| --- | --- |
| Production root | `output/studio/a32e5c2505fc454d96c3f734f3b3a469/` |
| Video / preview | `video.mp4`, `preview.mp4` in the production root |
| Narration | `narration.wav`, `narration.mp3` |
| Word / grouped subtitles | `word_boundaries.srt`, `subtitles.srt` |
| Script | `script.txt` |
| Voice timing/performance | `voice_report.json`, `voice_chunks/` |
| Visual review | `qa_contact_sheet.jpg`, `editorial_visual_review.json` |
| Thumbnail | `thumbnail.jpg` |
| YouTube API + audit | `youtube_verification.json` |
| Acoustic checks | `audio_transcription_check.json`, `date_acoustic_check.json` |
| Equal-loudness samples | `output/voice_lab/comparison/kokoro_normalized.wav`, `edge_normalized.wav` |
| Real MCP voice evidence | `output/voice_lab/mcp_kokoro_evidence.json` |
| Plugin package | `output/videonews-ai-studio-0.3.11.zip` |
| Regression output | `output/voice_lab/final_regression.log` |

The full local regression suite passed **391 tests**, with two optional tests
skipped in the default invocation. The explicit live Kokoro suite separately
passed all **8 tests in 36.96 seconds**. Real CPU speech, alignment, both FFmpeg orientation fixture
checks, preview/final media, actual MCP calls and the public YouTube API result
are distinguished from mocked unit tests. A clean Windows installation was not
repeated during this production run.

## Source changes

Created:

- `scripts/kokoro_worker.py`
- `scripts/tts_service.py`
- `tests/test_kokoro_production.py`
- `docs/KOKORO_PRODUCTION_ACCEPTANCE.md`

Modified:

- `.env.example`, `README.md`, `requirements.voice.lock.txt`
- `scripts/runtime_config.py`, `scripts/setup_local_voice.ps1`
- `scripts/studio_mcp.py`, `scripts/studio_server.py`
- `scripts/media_quality.py`, `scripts/video_assembler.py`
- `scripts/desktop_mcp_smoke.py`
- `tests/test_studio_mcp.py`, `tests/test_media_quality.py`
- `docs/LOCAL_VOICE.md`, `docs/CHATGPT_STUDIO.md`
- `chatgpt-plugin/plugin.json`, `chatgpt-plugin/.codex-plugin/plugin.json`
- `chatgpt-plugin/skills/news-video-workflow/SKILL.md`

No source files were deleted. Local `.env` selects Kokoro without changing
existing secret values; models, audiovisual assets and logs remain outside Git.
