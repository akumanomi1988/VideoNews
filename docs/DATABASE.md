# Local persistence

VideoNews uses local SQLite databases for article/job reconciliation and
project-scoped JSON files for editorial work. No Telegram user database is
required.

## Processed articles

`processed_news.db` stores source URLs and legacy article-analysis fields. The
`processed_news` table uses the URL as its primary key and stores title,
summary, analysis measurements, and processing timestamp. Studio news search
uses the URL check to flag prior work; it does not treat old heuristic scores
as audience analytics.

The `scripts.dbControllers.processed_news_controller` module exposes
`is_url_processed(url)` and `save_processed_news(news_data)` for this store.

## Studio projects

By default, projects are stored in `output/studio/<project-id>/project.json`.
Set `VIDEO_STUDIO_DIR` to change the root. JSON is written atomically and uses
schema version 2. It contains source references, editorial briefs, script and
storyboard versions, production format, asset provenance and checksums, YouTube
metadata, and current artifact paths. Generated media stays inside the project
folder. The `_imports` inbox is scoped under the same Studio root.

Long-running Studio jobs have durable status records in
`output/studio/jobs/<job-id>.json`. Jobs interrupted by a process restart are
marked `interrupted`; they are never silently replayed. Inspect completed video
and uncertain upload records before taking another action.

## Upload authorization

One-use owner grants are stored in a project-local
`owner-authorization.json` file and are excluded from MCP responses. They bind
the video SHA-256, YouTube channel ID, private privacy status, operation, and
expiry. A grant is consumed before the upload attempt. An unknown outcome moves
the project to `upload_unknown`, where an automatic retry is forbidden.

## Reconciliation database

`VIDEO_JOBS_DB` defaults to `videonews_jobs.sqlite3`. The
`scripts.job_registry` module keeps URL-level production claims, state changes,
and uncertain external publication outcomes. Operators must reconcile remote
YouTube state before retrying a job whose upload result is unknown.

## Backups and secrets

Back up `processed_news.db`, `videonews_jobs.sqlite3`, and `output/studio` as
needed. Keep `.env`, `.secrets`, OAuth tokens, and API credentials outside Git.
The Windows bootstrap preserves existing credentials and generated videos.
