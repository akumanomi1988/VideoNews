# Local audio, music and graphics upgrade

Kokoro productions now retain `narration.wav` as `project.voice`. No MP3 is
required; `tts.export_mp3=true` in settings enables an auxiliary copy. Historical
projects keep their recorded audio path, including Edge MP3. Published projects
are never migrated. FFmpeg exports AAC with `VIDEO_AUDIO_BITRATE=320k` by default;
the encoder can choose a lower effective rate for simple mono material. The
unconditional 48 kHz output resample has been removed.

`audio_engine.export_audio` provides optional 65 Hz highpass, gentle +1 dB
intelligibility EQ, optional 1.5:1 compression, peak limiting and measured two-pass
normalization. PCM comparison exports preserve the source sample rate. The current
renderer retains its existing loudness stage; the optional EQ/compression chain
is available as an explicit preprocessing operation, not automatically enabled.

## Licensed music

`MusicLibrary(root)` reads `catalog.json`. Each entry requires exactly `id`,
`name`, `author`, `file`, `duration`, `category`, `intensity`, `license`, `source`,
`attribution`, `commercial_use` and `moods`. File paths must stay inside the library.
Categories are Science & Space, Technology, Economy, Documentary, General News,
Dramatic / Tension, Neutral Ambient. Moods are ambient, cinematic, minimal,
dramatic, none. Explicit track IDs never silently fall back. No compatible track
means no music plus a stored reason. License assertions are supplied by the owner;
the engine cannot independently establish rights from a string.

Download authorized tracks yourself from YouTube Studio > Audio Library. Save
the track and its actual license/attribution record, including commercial-use
permission, in the local catalog. Do not assume that arbitrary YouTube audio is
licensed. No music was downloaded or used in this demonstration.

MCP `select_music(job_id, mood, category)` persists the decision. Rendering uses
the selected file; an explicit no-track decision suppresses legacy configured
music. The audio processor supports sidechain ducking and measured normalization.
Selected tracks are checked again against the catalog and SHA-256 before rendering;
changed files or revoked commercial permission fail instead of selecting another
track. The renderer prepares a circular crossfade loop unit. A real two-tone
regression measures attenuation of the music frequency during the speech region.
This verifies ducking behavior, not subjective intelligibility of arbitrary music.
Automatic attribution insertion remains unfinished; retain required credits.

## Native graphics

`generate_graphic(job_id, scene_id, specification)` is asynchronous. Poll `get_job`.
The specification is validated by `GraphicSpec`; unknown fields and unregistered
source URLs fail. `kind` accepts timeline, comparison, statistical_chart,
process_diagram, flow_diagram, fact_card, scientific_schematic, geographic_map.
Items have label, source_url and optional numeric value. Charts require a unit
and nonnegative values. The shared renderer produces source/provenance receipts,
safe-area PNG frames and optional local H.264 clips. Fonts use Windows Arial.

`animation` accepts none, reveal, bars, highlight. Animated items require ordered
`cue_word_indices` relative to the scene (zero-based normalized words). Studio
requires aligned narration first and derives cue seconds and scene duration from
the real SRT. Explicit conflicting cue seconds fail. A binding to the SRT hash
blocks stale animation timing after narration changes. The ordinary assembler can consume
the scene's animation clip instead of its still and verifies the clip hash.

Maps require one closed GeoJSON exterior Polygon plus `geometry_source` matching
a registered source. No geometry is bundled or inferred. Holes, multipolygons,
antimeridian handling and cartographic projections beyond the local schematic
are unsupported. Scientific diagrams and comparisons currently share the basic
label layout; richer domain-specific relationships remain unfinished.

## Real local evidence

Run `python -m scripts.av_upgrade_demo` with FFmpeg on PATH. It reads Lucy's
published artifacts without editing them, generates three full-length PCM
comparisons, three graphics and two animated clips, then renders a separate
60-second landscape demonstration. No Azure request or upload is performed.

Artifacts: `output/av_upgrade/A_original.wav`, `B_mp3.wav`, `C_processed.wav`,
their measurement JSON files, `demo.mp4`, `contact.jpg`, `qa.json`, `graphics/`.
Equal-loudness signals are provided for listening; bitrate alone is not a quality
judgment. A/B are normalized comparison copies, not replacements for raw source.

Graphics receipts commit only after generation succeeds. Valid outputs are reused
by specification and checksums; corrupt outputs regenerate. Repeating the same
Studio scene request retains its asset rather than adding duplicates. Fonts are
cached; chart and map labels reserve space for data and geometry. Nonfinite values
and malformed music catalogs fail validation.

`python -m scripts.av_hardening_acceptance` creates a separate local Lucy clone,
copies its WAV and timed subtitles, generates three native graphics (two animated),
tests repeated requests, renders the complete video and runs QA. It never uploads
and checks that the published source MP4 hash remains unchanged. Evidence goes to
`output/av_upgrade/hardening_acceptance.json` and the new project folder.

Audio processing now compensates limiter latency, rejects silence/nonfinite
loudness measurements and commits PCM output atomically after successful export.
FFmpeg operations have bounded timeouts and isolated stdin. A failed export leaves
the previous output untouched.

Job/project JSON now commits via atomic replacement, with bounded local retries
for Windows sharing conflicts. Readers cannot see a truncated job record. Job
records retain their worker PID; starting another Studio instance does not mark
jobs owned by a still-running process as interrupted. Dead workers still produce
an explicit interrupted state rather than an automatic external-service retry.

The hardened acceptance project is `8e324c176bde4262b98e16f4b49e3955`. Its actual
219.958-second 1920x1080/24 FPS render passed full-stream decode, with 9.7 ms A/V
drift, -17.3 LUFS, -4.5 dBTP, no black intervals and no QA issues. Three native
graphics, two acoustic-word-bound animations, repeat-request reuse and unchanged
published-source SHA-256 were observed. The contact sheet was inspected, and
truncated test labels were corrected before the final render. No Azure credits
or YouTube upload were used; music remained explicitly disabled in this clone.
The final Windows regression run passed 419 tests with two optional tests skipped.
The packaged MCP smoke test exited zero with 27 tools, handshake, status, project
listing and cold native-image import verified. This is local MCP evidence, not a
new ChatGPT Desktop UI acceptance claim. The private plugin was updated and read
back at version 0.3.13 with the same identity and permissions.

Remaining work includes richer domain-specific layouts, all requested motion
primitives, automatic attribution insertion and expanded model-independent
storyboard/audio/music contracts. This document does not certify those features.
