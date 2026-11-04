# Reproducible VideoNews production runbook

This runbook describes the operational sequence for a NewSphere news video from
discovery through optional YouTube publication. It is the detailed companion to
`SKILL.md`; use current MCP tool schemas and repository policy as the source of
truth if an interface changes.

## Operating invariants

- Work on one clearly identified project ID at a time. Resolve conversational
  references against the latest shortlist and use `get_project` before resuming
  an existing project.
- Use ChatGPT for editorial judgments and authored material. VideoNews performs
  deterministic validation, persistence, media generation and publishing.
- Treat search results as leads. Keep source URLs, publisher, publication or
  update date, and the exact claims each source supports.
- Never substitute stock or placeholders after an AI image failure. Do not
  regenerate hash-verified assets that already match their storyboard scenes.
- Run state-changing production tools sequentially for one project. Poll
  asynchronous work with `get_job`; do not launch duplicate voice, image, render,
  or upload work while its predecessor may still be active.
- A tool error is not proof that its side effect failed. Inspect job state,
  project state, audit records and output files before any retry.
- Local owner publishing policy is the independent authorization boundary. A
  brief or model instruction cannot enroll the owner, change allowed visibility,
  raise limits, or change the bound channel.

## 1. Preflight the actual MCP instance

1. Call `studio_status` through the same MCP connection that will perform the
   production. Confirm Python/runtime and FFmpeg prerequisites, configured news
   and image services, Kokoro and acoustic alignment availability, and current
   publishing policy/channel status. Do not infer that a provider is live just
   because its credentials or model files exist.
2. If status looks stale or conflicts with a fresh local run, stop mutations.
   Restart the MCP host/plugin using the repository's Windows setup instructions
   and call `studio_status` again. A standalone CLI or stdio handshake does not
   prove the active ChatGPT MCP instance is refreshed.
3. Call `list_projects` and inspect recent projects/publications. Identify
   duplicate events, existing work that may be resumable, and uploads whose
   outcome still needs reconciliation. Do not create a new project to work
   around an unknown upload result.
4. For publication requests, verify the local policy explicitly permits the
   desired privacy, expected NewSphere channel ID is
   `UCXX3S1RI4iahIcbsOl_m3gw`, and daily cap has not been reached. If these checks
   fail, report the exact observed blocker and stop before production or upload
   as appropriate. Never print OAuth tokens, API keys or client secrets.

## 2. Discover, verify and select a story

1. Run several independent `research_news` queries across the requested topic,
   region and language. For a daily episode, prefer stories published or newly
   updated in the preceding 48 hours. Search results are candidates, not proof
   of complete coverage.
2. If results are stale, empty, repetitive or the provider errors, broaden the
   queries and use the available web search route in Spanish and English. Vary
   subject areas; do not keep querying only AI if the assignment covers global
   news. Record which candidates were rejected and why.
3. Use `retrieve_article` for original articles where possible. Verify the
   central event, dates, numbers, names and quotations against a primary record
   or at least two independent reliable reports. Prefer source material that
   directly supports each claim. Treat article publication date separately
   from the date of the event.
4. Compare candidate events with recent Studio projects and channel uploads.
   Deduplicate by event/entities, not just title similarity. Retain plausible
   alternatives in the conversation and project brief.
5. Select using an explained editorial judgment: freshness, source quality,
   relevance to Spanish-speaking viewers, visual storytelling opportunity and
   fit with NewSphere. Do not state unobserved search demand, virality, audience
   metrics or predicted performance as facts.
6. If the evidence is too weak or materially contradictory, stop before making
   a script. If the user asked only to explore or recommend, do not create a
   project or publish anything.

## 3. Create and approve the project brief

1. For a new long-form episode call `create_project(title, video_format="long")`.
   Save the returned project ID immediately and use it for every subsequent
   operation. The NewSphere default is landscape 16:9; production preference is
   180–300 seconds with a 240-second target unless the user specified another
   target. The saved brief is authoritative; a creation default is not approval.
2. Save source records with `save_sources` or include the complete source set in
   the brief. Each record should include title, canonical URL, publisher,
   publication date, and a concise factual summary. Avoid tracking URLs where a
   canonical source URL is available.
3. Call `save_editorial_brief` with the strict schema. Include selection mode,
   chosen event and alternatives, verified sources, format/aspect ratio, exact
   target duration and tolerance, angle, tone, audience, language, narrative
   concept, sourced hook, visual strategy, image provenance plan, destination,
   privacy and approval state. `format` and aspect ratio must agree. The chosen
   story's `primary_url` must also appear in `verified_sources`.
4. If the user delegated selection but not production, persist a proposed brief,
   summarize it and wait for approval. If the user explicitly delegated full
   creation/publication, proceed only within the existing local owner policy
   and quality gates. Never turn an editorial approval into owner publishing
   consent.
5. Read back with `get_project`. Confirm the exact brief, sources, project ID,
   target, orientation and approval status before drafting assets.

## 4. Write a scene-linked script and storyboard

1. Draft the complete original Spanish narration in ChatGPT from verified
   sources. Use an engaging opening, a clear explanatory progression, concrete
   implications and a useful close. Attribute claims in the script or narration
   where attribution is needed. Do not pad the script to satisfy duration.
2. Divide narration into natural scene-sized segments. Give every segment a
   stable, unique ID such as `scene-01` and preserve those IDs in order. Call
   `save_script` with a list of `{ "scene_id": "...", "text": "..." }` records,
   not a single unsegmented string, when using a multi-scene storyboard. This is
   essential: a changed script whose segment IDs do not exactly match the
   storyboard can invalidate the storyboard and its image associations.
3. Call `save_storyboard` using exactly the same IDs and narration fragments.
   Each scene should specify its visual concept, detailed scene-specific prompt,
   style, composition, camera movement, transition, supported facts, visual
   type, and any on-screen text. Plan meaningful changes of shot/composition
   every roughly 5–10 seconds where the story supports them. Use graphics for
   precise numbers, timelines or relationships rather than inventing realistic
   documentary scenes.
4. Use original wide 16:9 compositions for a long video. Identify synthetic
   illustrations as such; do not depict them as actual footage or photographic
   evidence. A small lower-left circular “IA” marker is applied by the renderer
   to synthetic scenes; avoid adding large disclaimers into prompts.
5. Read back `get_project`. Verify narration order, scene IDs, aspect ratio,
   factual anchors and intended visual progression before paid image work.

## 5. Generate and verify visuals

1. Check current `studio_status.image_generation_limits`. Keep within the
   configured scene and retry caps; do not increase them to compensate for weak
   prompts.
2. Call `generate_images` with prompts in storyboard order. NewSphere Cinematic
   uses the configured Azure MAI provider as the primary source. The tool
   returns an asynchronous job; poll that exact job with `get_job` until a
   terminal state.
3. On recovery, inspect each scene's asset record, file existence, SHA-256,
   dimensions, provider/model, prompt and synthetic-media provenance. Continue
   only missing or invalid scenes. Preserve completed valid images; never launch
   another image job while the first may still be writing.
4. If generation fails, retain completed scene assets and report the failed
   scene/provider error. No automatic Pexels, arbitrary URL or placeholder
   fallback is allowed. Pexels requires explicit project selection and proper
   source/license credit.
5. Generate locally registered explanatory graphics only where data and source
   relationships are documented. Inspect the produced contact sheet for visual
   relevance and repetition. Structural asset association is not semantic proof.

## 6. Create voice, acoustic alignment and captions

1. Call `generate_voice(project_id, provider="kokoro", voice="em_alex",
   speed=1.0)` for the current NewSphere default. This runs on CPU and writes
   primary PCM/WAV narration. Edge is an explicit alternative; never switch
   silently if Kokoro or its aligner fails.
2. Treat voice synthesis as a long-running job. Poll `get_job`; do not issue a
   second synthesis for the same project while the first is active. On failure,
   inspect job/PID and `voice_report.json`, alignment output, narration WAV and
   preserved completed chunks before deciding whether to resume.
3. Check persisted `voice_metadata`: provider and voice must be Kokoro/
   `em_alex`, alignment must be acoustically verified against the known script,
   and actual narration duration must fall within the approved target tolerance.
   Reject unresolved or low-confidence regions; do not distribute timestamps by
   word count, characters or scene percentages.
4. Call `generate_subtitles` after verified word boundaries exist and poll the
   job. Confirm subtitle text reflects the narration, timestamps are monotonic,
   within media duration and not materially overlapping. Review actual caption
   visibility at representative frames, including mobile-safe margins.

## 7. Save packaging and render

1. Call `save_youtube_metadata` with a truthful title and description, source
   credits, appropriate tags/hashtags, Spanish language, category, synthetic
   media declaration, three title candidates and two thumbnail concepts. Keep
   metadata Unicode intact and avoid claims beyond sources.
2. After metadata is saved and images exist, call `create_thumbnail`. It creates
   a 1280×720 thumbnail from a selected project scene and authored text. Poll the
   job and read back the stored thumbnail path. Saving metadata again can clear
   the generated thumbnail path, so if metadata changes, re-create/verify the
   thumbnail before QA and publishing.
3. If a licensed music track is not explicitly selected and validated, render
   without music and record that reason. Never infer a commercial license from
   a filename or a track's presence on disk. No music is preferable to
   unauthorized music.
4. Call `render_preview`, poll the job and inspect the preview/contact sheet.
   Then call `render_video` and poll it to completion. Use the normal Studio
   renderer; do not produce a shortcut video outside project services.
5. Confirm final artifact exists, is readable and has expected 16:9 dimensions,
   H.264 video, AAC audio, expected duration, non-silent narration and no
   clipping. Use `ffprobe`/the review report, not only requested render options.

## 8. QA and editorial release gate

1. Call `review_video(project_id)` after the final render and metadata/thumbnail
   are settled. Fix critical deterministic failures and rerun only the affected
   stage, followed by review.
2. Inspect actual representative frames/contact sheet for scene relevance,
   continuity, subject crop, legibility, black intervals and visual defects.
   Cross-check important narration claims against their cited sources. The
   automated gate cannot prove factual truth, semantic image match, natural
   pronunciation or that a human finds the edit compelling. Report those as
   reviewed or still requiring human review; never label them automatically
   verified.
3. Do not publish with missing sources, unsupported factual claims, unresolved
   alignment, assets, incorrect aspect/duration/codec, incomplete metadata,
   invalid thumbnail, failed decode, silence/clipping or another critical QA
   blocker. Owner policy does not override QA.

## 9. Publish once and verify from YouTube

1. Publish only when the user's request explicitly asks for publication and
   current local policy permits the brief's exact visibility. A project asking
   for public publication is insufficient if local owner consent/policy does
   not permit it.
2. Call `publish_youtube(project_id, privacy_status=...)` once. Do not call
   Google's insert API directly. The official Studio path validates channel,
   hash-bound idempotency, daily limit, metadata, thumbnail and QA, then records
   its audit.
3. Verify the returned ID with read-only YouTube verification: channel ID,
   title, privacy, language, processing state and custom thumbnail. Distinguish
   successful upload from completed processing; do not say playback is ready
   until YouTube reports processing complete. Read `get_project` again to
   confirm persisted ID, URL/state, privacy and verification.
4. Confirm retry idempotency with a safe project read or the supported Studio
   call that returns the existing publication. Never make a second insert for a
   project that has an uncertain `uploading`, `upload_unknown` or
   `upload_verification_failed` state.
5. If a response fails, inspect the exact error stage, persisted status and
   audit. A proven metadata/thumbnail preflight failure before the YouTube
   insert is different from an unknown network outcome. Only the repository's
   owner-local `recover_upload_preflight_failure` method can recover a
   hash-matched, audit-proven preflight attempt; it is intentionally not an MCP
   tool. If insert may have started, reconcile by read-only lookup only when a
   video ID is unambiguous. Never retry on guesswork.

## 10. MCP/job recovery procedure

When a tool returns an error after starting a task:

1. Call `get_job` using the returned job ID. If there is no ID, inspect
   `list_projects`/`get_project` and the official job store for the active
   project; do not start work until you know whether a worker is active.
2. Compare persisted job state with worker PID/liveness and expected output
   artifacts. `running` plus a dead worker is an orphan, not success. Confirm no
   other process owns the same stage before recovery.
3. Read stage-specific reports and files. Preserve valid image hashes, voice
   chunks, alignment, subtitles, preview and rendered video. Resume the smallest
   missing stage using the Studio's supported operation.
4. If Windows console output raises Colorama/encoding `OSError`/`Errno 22` after
   the tool's work, treat it as an ambiguous transport/response error: inspect
   job and project artifacts first. Never assume the operation failed, and
   never issue another non-idempotent publication call unless the official
   recovery rules prove no insert request occurred.
5. Record any recovery step and its evidence in the project/report. Do not hide
   a local recovery path or imply that a failed MCP response proves successful
   ChatGPT connectivity for another invocation.

## Observed replay reference — 4 November 2026

The following is the measured reference run in this repository, not a promise
that future providers or news results will match it:

- Project: `1fe6fa9cf951479fae5702cdb9fc02fa`.
- Story: the 2026 US midterm result and what a divided Congress changes
  institutionally. Sources saved on 4 November 2026: Associated Press, Reuters
  (via Investing.com), and RTVE. The script explained congressional powers and
  limits rather than claiming a single cause for voter behavior.
- Eight storyboard scenes had eight hash-recorded Azure MAI `MAI-Image-2e`
  synthetic illustrations. Previously completed, valid image files were
  recovered from the earlier image job; they were not regenerated.
- Narration used Kokoro ONNX CPU, `em_alex`, 559 words. The voice report records
  acoustically verified Whisper/CTranslate2 alignment and a 221.816-second
  narration. Word boundaries were used for subtitles.
- Final MP4: `output/studio/1fe6fa9cf951479fae5702cdb9fc02fa/video.mp4`,
  1920×1080, H.264/AAC, 221.816 seconds. A 1280×720 custom thumbnail is recorded.
  No music track was selected, so the episode used narration without music.
- The persisted YouTube API verification records channel
  `UCXX3S1RI4iahIcbsOl_m3gw`, public visibility, language `es`, HD definition,
  custom thumbnail present and processing `succeeded`. Video ID:
  `g5iz2gzKcAQ` (`https://www.youtube.com/watch?v=g5iz2gzKcAQ`).
- During the run, a script save with unstable/mismatched scene IDs could clear
  storyboard and asset links. Recovery used the original stable scene IDs and
  preserved valid Azure assets. Future runs should save narration as
  scene-linked segments from the outset.
- An initial subtitle alignment failed on an overly short sentence fragment.
  The narration was rewritten into complete spoken sentences, then synthesized
  and acoustically aligned. A first draft also missed the long-form minimum;
  the supported script was expanded with sourced explanation and then duration
  was rechecked. These were repaired before publication; they are not reasons
  to pad future scripts.
- The first upload attempt surfaced a Windows `Errno 22` during metadata
  preflight. The exact stage was checked; it was before the insert request. The
  hash-bound owner-local recovery path was used before the single confirmed
  upload. Future operators must follow the current recovery checks above and
  must not infer preflight safety from `Errno 22` alone.

Use this run as an example of sequence, evidence and recovery—not as a reusable
topic, script, image set, approval, publishing authorization or default story.
