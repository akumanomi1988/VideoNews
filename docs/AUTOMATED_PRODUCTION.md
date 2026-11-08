# Production on every invocation

Each explicit create-and-publish invocation produces one new, distinct NewSphere
episode, even when another episode was published on the same local or UTC date.
Scheduled and manual invocations use this same rule. A resumed invocation keeps
its active project and never creates a second upload for that project.

Automatic owner enrollment has no daily upload cap by default. The persisted
`max_uploads_per_day: null` means unlimited; legacy positive caps remain readable.
The owner-local command below removes an existing cap, verifies the saved OAuth
channel without a browser, preserves visibility consent and audits the change:

```powershell
.\.venv\Scripts\python.exe -m scripts.owner_publish_policy remove-upload-limit
```

This command cannot enroll a missing policy, authorize a new channel or add a
visibility mode. `studio_status` reports `publishing_uploads_unlimited: true`
when the active server has loaded an unlimited policy.

## Automation instructions

1. Read the repository-local `news-video-workflow` skill and call `studio_status`.
   Verify the NewSphere channel, public consent, FFmpeg, Kokoro/alignment and image
   provider. If MCP OAuth diagnostics disagree with the actual token, use the
   documented non-interactive channel verification and official local recovery.
2. Inspect recent projects for repeated events, active jobs and uncertain uploads.
   Prior successful uploads today never consume a production quota.
3. Search at least four distinct global queries in Spanish and English. Treat
   provider results as leads. Broaden stale or irrelevant results through current
   web search across science, technology, economy and international affairs.
4. Choose a fresh event from the last 48 hours, supported by a primary record or
   independent reliable reporting. Explain editorial interest without inventing
   audience metrics. Search another topic when the first repeats an existing event.
5. Create a new long-form 16:9 project, 1920x1080, Spanish narration, NewSphere
   Cinematic, target 210 seconds with 30-second tolerance. Persist sources,
   approved brief, original scene-linked script and matching storyboard IDs.
6. Generate configured original visuals, Kokoro em_alex WAV and acoustic alignment,
   captions, thumbnail, preview and final MP4. Preserve valid work during recovery.
   Use music only with verified rights. Keep bounded failure retries; an unlimited
   publication count does not mean unlimited retries of a failed operation.
7. Run technical QA and inspect actual frames and source support. Repair critical
   defects before publication. Distinguish automated checks from editorial judgment.
8. Publish through the official Studio method once with public visibility. Verify
   channel, title, metadata, thumbnail and completed processing through YouTube
   reads. Reconcile uncertain outcomes; never repeat an uncertain insert. Report
   the observed URL, project, media properties, QA and any actual blocker.

External provider quotas, billing balances and rate limits are controlled by their
services. Report their actual errors rather than claiming they have been removed.

The scheduled task prompt must use these rules rather than an earlier
one-publication-per-date prompt. Updating repository files alone does not update
the separately persisted task prompt. Already running MCP hosts may need a reload
to use changed Python modules; a fresh official local Studio uses the current code.
