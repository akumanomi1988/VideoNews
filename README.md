# VideoNews

A local-first, Python 3.11 news-to-video production engine controlled through Telegram.
Create narrated, illustrated, subtitled vertical shorts and horizontal news videos
from category feeds, headlines, article text, URLs or ranked viral news.

> Migration note: Telegram now uses **one rendering engine**
> (`NewsVideoProcessor`) for every input type. The older
> `scripts/pipeline.py` abstractions remain in the repository for
> compatibility, but they are not invoked by Telegram.

## Features

| Input | Telegram command | Output |
| --- | --- | --- |
| News categories | `/news_category` | Select a news item and generate a video |
| Headline/topic | `/topic_shortnews`, `/topic_longnews` | 9:16 or 16:9 |
| Full article | `/text_shortnews`, `/text_longnews` | 9:16 or 16:9 |
| Public article URL | `/url_shortnews URL`, `/url_longnews URL` | 9:16 or 16:9 |
| Viral discovery | `/headless [1-20]` | Scored stories; ignores published URLs |
| Settings | `/settings`, `/show_settings` | Non-secret preferences only |

Also includes optional visual styles, automatic thumbnail generation, narration,
SRT subtitles, FFmpeg video assembly, local exports, YouTube uploads, TikTok
creator inbox transfers, SQLite deduplication and a lightweight monitoring UI.

## Installation (recommended)

Requires **Python 3.11** and **FFmpeg** available in PATH. For some legacy text
effects, ImageMagick may also be needed.

```sh
git clone https://github.com/akumanomi1988/VideoNews.git
cd VideoNews
python -m venv .venv
# Activate .venv for your platform.
pip install -e ".[dev]"
cp .env.example .env
```

The example `.env` must be edited before using the bot:

- `TELEGRAM_BOT_TOKEN`: token issued by Telegram for your bot.
- `TELEGRAM_ALLOWED_USER_IDS`: **mandatory** comma-separated numeric owner IDs.
  The bot refuses to start without at least one authorized ID. This restriction
  protects API quotas, configuration and video publishing.
- `OLLAMA_URL` and `OLLAMA_MODEL`: default local LLM. Alternatively set
  `GROQ_API_KEY` or Azure OpenAI credentials and disable Ollama with
  `OLLAMA_ENABLED=false`.
- `SERPAPI_API_KEY`: category and headless news discovery.
- `PEXELS_API_KEY`: stock photos. Missing media falls back to a text card.
- `TTS_VOICE`: default is `es-ES-ElviraNeural` via Edge TTS.
- `MEDIA_SOURCE=pexels`: default. To generate with the optional Azure image
  endpoint, configure `AZURE_IMAGE_ENDPOINT`, `AZURE_IMAGE_API_KEY` and set
  `MEDIA_SOURCE=huggingface` (historical option name).

Optional JSON preferences can live in `settings.json`. For a clean template
copy `settings.example.json`, but **do not put production API keys in JSON**.
Environment variables take precedence for all sensitive provider keys. The
Telegram settings editor only allows non-secret values.

## Run

```sh
python telegram_bot.py
```

By default, `VIDEO_UPLOAD_ENABLED=false`. Videos are copied into `output/`
so that generation can be validated without uploading publicly. All render
jobs use unique directories below `.temp/jobs/`. Local output and per-job JSON
metrics survive cleanup.

To publish to YouTube, provide OAuth client secrets at
`.secrets/client_secret.json`, then configure:

```dotenv
VIDEO_UPLOAD_ENABLED=true
VIDEO_UPLOAD_PLATFORM=youtube
```

The first YouTube authorization can require a local browser. Do not put OAuth
token files in version control.

For TikTok, set `VIDEO_UPLOAD_PLATFORM=tiktok` and configure a user-authorized
`TIKTOK_ACCESS_TOKEN` with the `video.upload` scope. The v2 API sends the
video to the creator's inbox; **the creator must finish publishing in TikTok**.
A separate audited Direct Post integration and explicit user consent are
required for direct publishing. Token refresh credentials can be provided with
`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` and `TIKTOK_REFRESH_TOKEN`.

### Voice providers

`TTS_PROVIDER=edge` is the supported low-cost default. Alternative choices
`elevenlabs` and `bark` are available: ElevenLabs requires authorized
credentials in a local JSON file configured by `ELEVENLABS_ACCOUNTS_FILE`;
Bark requires the optional local AI dependencies:

```sh
pip install -e ".[local-ai]"
```

The heavy extra also provides Whisper tools for offline transcription. For
ElevenLabs/Bark, subtitle boundaries are currently **estimated proportionally
from final audio duration**; Edge provides timing events. Check alignment before
publishing videos using alternate providers.

### Dashboard

```sh
python scripts/run_dashboard.py
```

Visit http://localhost:5000. The Flask monitor reads per-job records from
`metrics/`. Keep the dashboard bound to localhost unless adding authentication
and TLS.

### Docker

The Dockerfile uses Python 3.11 and installs the normal (lighter) dependencies.
Build it with `docker build -t videonews .` and pass `.env` through
`--env-file`. Bind-mount `output/`, `metrics/`, `.temp/` and `.secrets/`
to retain data and credentials between container restarts. Do not embed
`.env` or credentials inside an image.

## Tests

```sh
pytest -q tests/test_runtime_config.py tests/test_telegram_auth.py tests/test_url_safety.py tests/test_tiktok_uploader.py
```

These are unit regression tests; they do **not** replace an end-to-end render
against real news, LLM, media and publishing APIs.

## Security and operational notes

1. **Rotate any NewsAPI/Pexels keys previously committed in
   `pipeline_config.json`**. The active file is now sanitized but the keys
   remain in Git history; removing the file value does not revoke them.
2. Telegram is private by default and configured users can make potentially
   costly API calls. Do not expose the bot without quota enforcement.
3. Article URLs must point to public HTTP(S) targets. Extraction verifies
   redirects, response type and byte size. For high-trust multi-tenant services,
   enforce outbound egress restrictions against DNS rebinding at network level.
4. Generated claims require fact checking and source attribution. Editorial
   stance and tone are configurable through `NEWS_EDITORIAL_IDEOLOGY` and
   `NEWS_EDITORIAL_TONE`; defaults are factual and neutral.
5. Publishing is **opt-in** and integrations are unverified until exercised
   against authorized accounts. Bot jobs are serialized in-process to avoid
   accidental overlapping workloads; distributed worker scaling would require
   a persistent queue.

## Architecture

```text
Telegram commands / callbacks
  -> VideoService + authorization
    -> NewsExtractor (URL inputs) / category & viral fetchers
    -> NewsVideoProcessor (single active renderer)
      -> Chatbot (Ollama/Groq/Azure)
      -> Pexels/Azure media selection
      -> Edge/ElevenLabs/Bark TTS
      -> SRT + FFmpeg composer
      -> Local output / YouTube / TikTok inbox
    -> SQLite processed URL tracking + per-job metrics
```

License: MIT.
