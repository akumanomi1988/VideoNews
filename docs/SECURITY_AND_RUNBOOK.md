# VideoNews hardening and runbook

## Immediate incident response

Historical commits contained API credentials in `pipeline_config.json`. The current
branch removes those strings, **but Git history remains exposed**. Revoke and rotate
NewsAPI, Pexels and YouTube OAuth secrets with the respective providers. Review
provider audit logs and rotate any other credential ever committed. Do not reuse old
values. A history rewrite alone cannot make an exposed secret safe.

## Secure setup

1. Use Python 3.11 with FFmpeg and ImageMagick available in PATH.
2. Copy `.env.example` to `.env`; provide `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_ADMIN_USER_IDS` (comma-separated Telegram numeric user IDs).
3. Set the provider credentials needed by the selected workload, such as
   `SERPAPI_API_KEY`, `PEXELS_API_KEY`, and/or `AZURE_IMAGE_*`.
4. Optionally copy `settings.runtime.example.json` to `settings.json` to modify
   non-secret settings. Environment values override corresponding JSON settings.
5. Install with `python -m pip install -e .` (or build the Dockerfile) and run
   `python telegram_bot.py`.
6. For monitoring, separately run `python -m scripts.run_dashboard` with
   `DASHBOARD_HOST=127.0.0.1`. Do not expose the dashboard publicly without
   an authentication gateway.

## Publish policy

Videos are rendered to `output/` by default; the bot will not upload them.
To upload to YouTube, supply the OAuth client file locally with
`YOUTUBE_CREDENTIALS_FILE` and set `YOUTUBE_UPLOAD_ENABLED=true`.
The default upload visibility is **private**. Set `YOUTUBE_PRIVACY=unlisted`
or `public` only when editorial review, fact checking and copyright checks are
completed. The opt-in flag does **not** remove these obligations.

The TikTok uploader intentionally raises NotImplementedError instead of reporting
a false success. YouTube OAuth may require an interactive initial authorization.

## Concurrency and limitations

Each render has a unique working directory. A process-local lock serializes heavy
jobs; cancellation of an asyncio wrapper does **not** stop the underlying thread.
Do not run multiple workers against the same filesystem without a durable queue.
Run end-to-end publishing tests with real credentials in a secure, isolated
environment. Python unit/syntax tests do not validate YouTube or image API behavior.

## Known follow-up work

- Durable multi-process jobs, retry/idempotency and cancellation.
- Quality assurance for fact-checking and script provenance before publishing.
- Integration tests for FFmpeg/Whisper, OAuth callbacks and live APIs.
- Production-ready TikTok OAuth integration, if required.
