---
name: news-video-workflow
description: Operate this repository's VideoNews AI Studio MCP workflow for sourced NewSphere news research, cinematic video production, QA, recovery, and owner-authorized YouTube publishing.
---

# Repository-local VideoNews workflow

This skill belongs to this checkout. Before operating VideoNews, read the
canonical plugin instructions and the repeatable production runbook:

1. `chatgpt-plugin/skills/news-video-workflow/SKILL.md` — intent handling,
   editorial decisions, project contract, tools and publication rules.
2. `chatgpt-plugin/skills/news-video-workflow/references/reproducible-production-runbook.md`
   — exact preflight-to-delivery sequence, recovery checks and the observed
   production reference.
3. Read the referenced script, visual and production-standard guidance in that
   skill when the current production needs it.

Use the MCP tools exposed by this repository's configured VideoNews server.
Start with `studio_status`, then operate one project ID sequentially. Confirm
actual tool results, persisted state and real artifacts; a local handshake is
not proof of a live ChatGPT connection. Never invent news, timing, provider
success, QA evidence or upload results. Do not bypass owner publishing policy,
and do not retry an upload with an uncertain outcome.

For the full step-by-step sequence, read the repository's
`chatgpt-plugin/skills/news-video-workflow/references/reproducible-production-runbook.md`.
The notes below capture failure modes that changed what a successful run means.

Follow the user's requested control level: exploration/recommendation stops
before production, creation stops before publication unless explicitly asked,
and create-and-publish proceeds only when the current local owner policy and
quality gates allow it.

## Operational lessons from real Windows production

- **Treat `studio_status` as instance-specific.** If the active MCP reports a
  missing token, stale settings, or unavailable capability while a fresh local
  Studio check disagrees, do not call the system healthy and do not mutate the
  project until you identify the instance/config difference. The local
  `VideoNewsStudio` method is an acceptable recovery path only when the active
  host is demonstrably stale and the Studio's own method is used. Report that
  recovery; never imply it was a ChatGPT Desktop MCP call.
- **Read the actual tool contract before calling it.** For `generate_images`,
  use the `StylePreset` enum key such as `NEWSPHERE_CINEMATIC`, not the display
  label `NewSphere Cinematic`. A rejected style is a preflight failure; check
  `list_assets` before retrying so completed paid assets are not regenerated.
- **Windows MCP workers must not emit Colorama output.** Colorama may wrap the
  host's protocol stream; `print()` can raise `OSError: [Errno 22]` before a
  provider call or after its side effect. Use structured job results/logging.
  If this error occurs, inspect `get_job`, PID/heartbeat, project JSON and file
  hashes before deciding whether to resume. Do not infer provider failure from
  the tool error alone.
- **Kokoro alignment failures are transcript-specific.** Read
  `alignment_failure.json`; very short sentence fragments can have low acoustic
  confidence. Rewrite only the problematic sentence naturally, preserve the
  exact scene IDs/order with `save_script`, confirm valid assets remain linked,
  and rerun voice once. Never invent word times or start concurrent synthesis.
- **Metadata preflight is not an upload.** The uploader currently accepts base
  language codes such as `es`; use `language: "es"` for YouTube metadata even
  when the narration/brief uses `es-ES`. Saving metadata clears the stored
  thumbnail path, so recreate the thumbnail and rerun `review_video` afterward.
  If metadata/thumbnail validation fails before `videos.insert`, verify the
  project remains `draft` and has no `upload_started` audit before correcting
  and retrying the official Studio publish method.
- **Keep the Madrid-local daily rule separate from the policy's UTC limit.**
  Before creating a daily episode, inspect audit and YouTube-confirmed uploads
  for the current `Europe/Madrid` calendar date. Any confirmed public upload,
  or unresolved public attempt for that date, blocks another production/upload.
  The persistent owner policy still independently enforces its configured cap.
- **Do not equate a successful render with editorial release.** Inspect the
  actual contact sheet, check source support claim by claim, and distinguish
  this judgment from automated QA. Do not publish if the story, visuals,
  metadata, duration, aspect ratio, codecs, audio or subtitle timing has a
  critical defect.
- **Verify the upload by reading YouTube.** Call the official Studio
  `publish_youtube` once. Then use read-only YouTube Data API lookup to verify
  exact channel ID, title, public privacy, upload/processing state, duration,
  definition, tags/language, source credits and thumbnail. Verify local project
  state and audit. If the insert outcome is uncertain, never call publish again;
  reconcile only an unambiguous matching video ID. A returned thumbnail URL is
  evidence of a thumbnail, but does not by itself prove the API's synthetic
  media flag; report that flag only if observed.
