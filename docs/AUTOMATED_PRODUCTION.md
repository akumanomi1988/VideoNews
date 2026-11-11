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

The maintained scheduler prompt is
[autonomous-production-task.md](../chatgpt-plugin/skills/news-video-workflow/references/autonomous-production-task.md).
Use its full contents when updating the existing scheduled task through the
host scheduler's official update tool. Read the saved task back and compare the
prompt; preserve its enabled state and trigger unless the user requests a
schedule change. Do not create another task or start a production to test a prompt
update.

The prompt loads the repository-local workflow and references every run. It
prioritizes Spain, admits exceptionally important international stories with a
specific audience rationale, uses three factual hook candidates and a source-linked
beat map, and requires useful visual coverage rather than repeated generic images.
It preserves the automation's explicit 210-second target with 30-second tolerance;
this is a task-specific brief rather than the general skill's 240-second default.
It requires acoustic alignment, the primary Kokoro WAV, licensed music or an
explicit no-track reason, actual artifact inspection, and one official public
upload with readback and per-project idempotency.

External provider quotas, billing balances and rate limits are controlled by their
services. Report their actual errors rather than claiming they have been removed.

The scheduled task prompt must use these rules rather than an earlier
one-publication-per-date prompt. Updating repository files alone does not update
the separately persisted task prompt. Already running MCP hosts may need a reload
to use changed Python modules; a fresh official local Studio uses the current code.
