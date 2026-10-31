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
Seamless loop crossfades, automatic attribution insertion and objective ducking
intelligibility regression coverage remain unfinished; do not certify that phase.

## Native graphics

`generate_graphic(job_id, scene_id, specification)` is asynchronous. Poll `get_job`.
The specification is validated by `GraphicSpec`; unknown fields and unregistered
source URLs fail. `kind` accepts timeline, comparison, statistical_chart,
process_diagram, flow_diagram, fact_card, scientific_schematic, geographic_map.
Items have label, source_url and optional numeric value. Charts require a unit
and nonnegative values. The shared renderer produces source/provenance receipts,
safe-area PNG frames and optional local H.264 clips. Fonts use Windows Arial.

`animation` accepts none, reveal, bars, highlight. Animated items require ordered
`cue_seconds` relative to the scene and `duration`. Derive cues from actual word
boundaries; the engine validates ordering/range but does not yet prove that each
cue corresponds to the intended spoken phrase. The ordinary assembler can consume
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

This is an implemented incremental upgrade, not acceptance of every requested
phase. Remaining work includes full music loop/ducking tests, richer layouts,
all requested motion primitives, narration-derived cue enforcement, expanded
strict storyboard/audio/music contracts and end-to-end tests of those contracts.
