# Complete audiovisual engine

## Production audio

New projects use Kokoro PCM/WAV as their primary narration and an explicit
per-project audio_settings contract. configure_audio accepts highpass, equalize,
compress, music_level (0-0.3), ducking (2-12), and bitrate_kbps (96-320).
Unknown fields and nonfinite values fail. Optional EQ is +1 dB at 2.5 kHz;
compression is a moderate 1.5:1. All processing remains CPU/FFmpeg based.

The normal render_video and render_preview paths call production_audio.master.
It measures loudness, produces a checksum-cached PCM24 master at the source rate,
and passes that WAV to VideoAssembler with audio_mastered=true. The assembler
then skips its legacy normalization: there is one mastering operation and one
lossy encode, final AAC. The actual acceptance FFmpeg command used mastered.wav
and contained no second loudnorm. Original narration is never overwritten.
Historical Edge MP3 sources remain usable; historical projects without settings
retain their old renderer behavior. Published projects are never migrated.

Run python -m scripts.audio_comparison after acceptance to create matched -16
LUFS listening copies of original WAV, legacy MP3 and the project master.
These comparison copies are not production intermediates. Measurements are not
claims about subjective voice naturalness or listening preference.

## Music

MusicLibrary reads an owner-managed catalog.json under VIDEO_MUSIC_LIBRARY.
Required fields: id, name, author, file, duration, category, intensity, license,
source, attribution, commercial_use, moods. Categories: Science & Space,
Technology, Economy, Documentary, General News, Dramatic / Tension, Neutral Ambient.
Moods: ambient, cinematic, minimal, dramatic, none.

select_music persists a deterministic compatible selection, including its SHA-256.
Before rendering, catalog membership, commercial permission, metadata, actual
file duration and bytes are checked again. Revocation, missing/changed files,
silence or invalid metadata fail; no silent substitution occurs. New projects
have no music until an authorized selection is made. No compatible track means
no music with a recorded reason. Existing legacy configurations remain readable.

A circular crossfade loop unit blends the end with the beginning, with source
rate preserved. Mixing applies configurable music level, sidechain ducking,
fade-in/out, peak protection and measured final normalization. Required credits
are inserted automatically into a managed [Music attribution] description block,
including when metadata is saved after music selection. Repeated saves are
idempotent; selecting none removes only the managed block. Excessive description
length fails instead of truncating mandatory credits. QA rechecks music permission
and attribution before any future publication.

No licensed channel track was available for this acceptance. The separate
music_engine_acceptance fixture synthesizes tones and is explicitly marked
NOT_FOR_PUBLICATION. Its measured music amplitude during speech was 0.1112 of
its amplitude during silence. The loop boundary sample step was 0.02783 versus
0.02805 maximum ordinary internal sample step; output duration was exactly 8 s.
These are objective synthetic-fixture checks, not human listening certification
of an unavailable commercial track. Download authorized resources via YouTube
Studio > Audio Library and retain the actual terms and attribution in the catalog;
never infer rights from a track's presence on YouTube.

## Graphics contracts and layouts

GraphicSpec is a strict versioned-by-renderer specification. Every datum references
a registered project source. Renderer asset IDs derive from the full specification
and layout version; completed receipts verify PNG/video checksums before reuse.
Repeated scene requests retain one asset; corrupt imported copies are repaired.

- timeline: ordered milestones on a rail with progression connections.
- comparison: separate contrasting panels with explicit state headers.
- statistical_chart: source-bound numeric bars, zero baseline and declared units.
- process_diagram: numbered ordered steps with arrows.
- flow_diagram: explicit directed relationships, not an implied list order.
- fact_card: emphasized concepts or values in reusable cards.
- scientific_schematic: entity nodes and explicit labeled relationships.
- geographic_map: source-bound geographic polygon, shown with an identified
  equirectangular projection rather than pretending to be a metric diagram.

All layouts support 16:9 and 9:16, safe margins, shared typography and color,
wrapped labels, numeric validation and deterministic composition. Excessive text
fails instead of clipping. Flow/scientific multi-node diagrams require relations:
objects with source and target item indices and a short label. Source membership
is not automatic scientific fact verification; editorial review remains required.

Production maps require import_geometry(job_id, staged_filename, source_url).
The owner stages a real .geojson dataset in the existing import inbox. Its source
must be registered; its checksum and project-scoped copy are preserved. Then
use its geometry_id in generate_graphic. Inline geometry cannot replace the
registered dataset. Supported subset: one closed Polygon exterior, bounded valid
longitude/latitude, no holes, multipolygons or antimeridian crossing. No geometry
is generated or guessed. Coordinate/source factual correspondence still needs
editorial verification; geometric validation does not prove dataset truth.

## Motion and spoken phrases

Supported animation values: reveal, bars, highlight, timeline, path, move,
before_after. FFmpeg composes one reusable PNG layer per element and a base;
it does not render a new PNG for each video frame. Wipes use a single grayscale
alpha mask, movement uses timed overlay positions, and highlights/state switches
use deterministic time expressions. Effects are bounded by the next event.

Prefer cue_phrases, one phrase per item. Studio matches normalized words against
Kokoro/Edge's actual SRT and derives scene-relative cue_seconds and duration.
Repeated phrases require explicit one-based cue_occurrences. Missing, overlapping,
out-of-order and conflicting references fail. Legacy cue_word_indices remain
supported for compatibility and still refer to actual acoustic words. Supplied
free times that disagree with those words fail; no percentage or character timing
is used. Animation assets bind to the SRT hash to reject stale timing.

Example tool payload (after aligned narration exists):

```json
{
  "job_id": "PROJECT_ID", "scene_id": "SCENE_ID",
  "specification": {
    "kind": "comparison", "title": "Arrival versus flyby",
    "items": [
      {"label": "Arrival in the region", "source_url": "REGISTERED_URL"},
      {"label": "First flyby remains scheduled", "source_url": "REGISTERED_URL"}
    ],
    "animation": "before_after",
    "cue_phrases": ["Pero llegar", "El primer encuentro"],
    "cue_occurrences": [1, 1]
  }
}
```

The ordinary VideoAssembler consumes checked animation clips, adds transitions
on the same 24 FPS frame clock and preserves the narration timeline. MCP tools
expose strict AudioSettings/GraphicSpec schemas: content comes from the model,
validation and execution come from Python. generate_graphic remains asynchronous.
No model-specific SDK, paid LLM, browser framework, GPU or Docker is required.

## Real acceptance and reproduction

Run, with FFmpeg on PATH:

- python -m scripts.complete_av_acceptance
- python -m scripts.verify_animation_timing
- python -m scripts.music_engine_acceptance
- python -m scripts.audio_comparison
- python -m scripts.desktop_mcp_smoke
- python -m pytest -q

The normal production-renderer acceptance project is
ca9bf836ec5647d58e77f75ce6e860ca. It reuses Lucy's actual Kokoro WAV and existing
Azure images without editing or publishing the original. It contains five native
layout families and five phrase-anchored animation types, synchronized subtitles
and transitions. Every repeated graphic request was reused without duplication.

Observed final MP4: 1920x1080, 24 FPS, H.264/yuv420p + AAC, 219.9447 s.
Full decode passed with no black intervals, no clipping, -16.6 LUFS, -4.4 dBTP,
and 28 ms stream-duration drift. Representative frames were inspected. Acoustic
cue versus frame-clock drift was at most 5 ms. Final-MP4 regions were compared
against their scene clips after cue entry; maximum pixel mean absolute error was
0.100/255. No unsupported semantic verification is inferred from those metrics.

All seven motion primitives also generated actual clips and passed complete
FFmpeg decode tests. All eight static layouts were rendered using controlled
fixtures, with separate tests for distinct layout pixels, invalid data, source
constraints, phrase ambiguity, corruption recovery, published-project guards,
rights revocation, atomic persistence and audio mixing. The final regression run
passed 442 tests, with two optional tests skipped. The existing Windows i7-2600
CPU was used; no claim of real-time performance or subjective audio improvement
is made. Operations have bounded timeouts; assets are cached for recovery.

Artifacts under output/studio/ca9bf836ec5647d58e77f75ce6e860ca/:
video.mp4, qa_contact_sheet.jpg, qa.json, audio_analysis.json, audio_master.json,
animation_timing.json, animation_validation.json, acceptance.json, graphics/.
Comparisons: output/av_upgrade/complete_comparison/.
Synthetic mixing evidence: output/av_upgrade/music_fixture/analysis.json and mix.wav.
Tests: output/av_upgrade/final_complete_tests.log.

## Source changes

Created: production_audio.py, graphic_layouts.py, graphic_motion.py, music_credit.py,
complete_av_acceptance.py, verify_animation_timing.py, music_engine_acceptance.py,
audio_comparison.py under scripts/; tests/test_complete_av.py.
Modified: scripts/audio_engine.py, graphic_timing.py, graphics_engine.py,
studio_mcp.py, studio_server.py, video_assembler.py, desktop_mcp_smoke.py;
this document, plugin manifests and production skill. No files deleted.

Limits: only the documented geographic subset and small diagrams (up to six
items/twelve relationships) are supported. Licenses remain owner-supplied evidence;
no external licensed-music E2E is claimed. Human voice preference and a separate
ChatGPT Desktop UI session were not verified. Existing hosts must reload their
MCP connection to discover the updated schemas. No YouTube upload occurred.

Real MCP validation discovered 29 tools and successfully called configure_audio
and asynchronous generate_graphic with strict schemas. A recorded Edge MP3
was also mastered locally: both input and PCM output measured 20.424 seconds.
Evidence: output/av_upgrade/edge_compatibility/acceptance.json. The private plugin
was updated and read back as 0.3.14 with unchanged identity and permissions.

Static relationship labels are painted after node fills, and receipt migration
can refresh the still without re-encoding an unchanged motion clip. Scientific
bar scales preserve ratios even below 1e-12; no arbitrary epsilon changes the
plotted range. Both behaviors are covered by the final regression suite.

## MCP background-job reliability

The stdio host routes provider output per worker thread. Do not use
`contextlib.redirect_stdout` around a background task: it changes process-wide
stdout and can corrupt concurrent JSON-RPC messages. Job records persist the
host PID, worker thread, heartbeat, terminal result, and a bounded traceback.
`get_job` marks dead-process or stale running jobs as `interrupted` so they can
be inspected and resumed; stale queued jobs remain queued because they may be
waiting behind active work. After updating the server code, restart the host's
MCP process to load the new stdout routing and recovery behavior.
