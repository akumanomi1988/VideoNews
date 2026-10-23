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

## Windows 10/11 — instalación principal

Windows es la plataforma principal. No necesitas WSL, Docker, ImageMagick
para el renderizado FFmpeg principal ni activar manualmente el entorno virtual.

Desde PowerShell instala Git, **Python 3.11** y FFmpeg (build completa con
filtros `libass/subtitles` y codificador `libx264`):

```powershell
winget install -e --id Git.Git
winget install -e --id Python.Python.3.11
winget install -e --id Gyan.FFmpeg
```

Cierra y abre de nuevo PowerShell para actualizar PATH. Comprueba
`py -3.11 --version`, `ffmpeg -version` y `ffprobe -version`.
Instala VideoNews con **un solo script**, que valida las dependencias y ejecuta
pruebas de verdad en Windows, incluidos vídeos MP4 de 9:16 y 16:9:

```powershell
git clone https://github.com/akumanomi1988/VideoNews.git
cd VideoNews
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\bootstrap.ps1
notepad .env
```

El instalador selecciona Python 3.11, crea `.venv`, comprueba los códecs
de FFmpeg, instala dependencias, crea `.env` solo si no existe, conserva las
credenciales existentes y ejecuta `pytest`. Para reinstalar dependencias sin
repetir tests, ejecuta `bootstrap.ps1 -SkipTests`. No descarga modelos pesados
de IA ni añade claves de API ficticias.

Para el primer vídeo, configura un proveedor LLM real en `.env` (por ejemplo,
`OLLAMA_ENABLED=false` y `GROQ_API_KEY=...`, o un modelo Ollama accesible).
Mantén `VIDEO_UPLOAD_ENABLED=false`; usa `VIDEO_RENDER_RESOLUTION=360p`
para una prueba rápida. Ejecuta:

```powershell
.\.venv\Scripts\python.exe -m scripts.doctor --mode cli
.\.venv\Scripts\python.exe -m scripts.cli --title "VideoNews prueba local" --format short
.\.venv\Scripts\python.exe -m scripts.cli --title "VideoNews prueba local" --format long
```

Los MP4 se guardan en `output`. TTS Edge y cualquier servicio externo
requieren internet; las publicaciones reales YouTube/TikTok requieren credenciales
y una verificación separada. La CI de Windows usa el mismo instalador PowerShell
y comprueba los renderizados reales también en rutas con espacios y caracteres Unicode.

## Instalación alternativa (Linux/macOS)

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

## Run diagnostics before any production job

The CLI and Telegram share the same production engine. Before attempting an
end-to-end job, validate installation, codecs and required environment variables:

```sh
python -m scripts.doctor --mode cli
python -m scripts.doctor --mode telegram
```

Diagnostics never print API key values and do not call external APIs. They only
confirm configuration and local executable availability, not service reachability.

For direct command-line production (no Telegram credentials required):

```sh
python -m scripts.cli --title "A factual news headline" --format short
python -m scripts.cli --url https://example.com/article --format long
python -m scripts.cli --text-file article.txt --format short --style REALISM
```

Set `VIDEO_RENDER_RESOLUTION=360p` for quick video previews, `720p` for
drafts or `1080p` (default) for full resolution. Both 9:16 and 16:9 formats
preserve their aspect ratio. Set `VIDEO_SHORT_SCENES=8` (maximum 12) and
`VIDEO_LONG_SCENES=18` (maximum 48) to cap media generation and its API costs.
Scene order follows the generated script instead of being randomized.

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

Additional `test_offline_render_integration.py` uses the real engine and FFmpeg to render playable vertical and horizontal MP4s with deterministic provider fixtures. It is run in the GitHub pull request workflow. These tests still do **not** replace an end-to-end render
against real news, LLM, media and publishing APIs. The Azure/OpenAI-compatible REST adapter uses
HTTPS requests without requiring the separately installed OpenAI Python SDK.

## Durable job recovery and duplicate protection

URL and viral modes reserve each article URL in an on-disk SQLite database
(`VIDEO_JOBS_DB`, default `videonews_jobs.sqlite3`). Parallel attempts
cannot publish a story twice. Successful local or remote outcomes are
recorded before updating the legacy article index.

Network interruption after an external upload starts is **not** retried
automatically: the job remains `NEEDS_REVIEW` until the operator checks
YouTube or TikTok for the actual video. This avoids accidental duplicate posts.
Interrupted `RESERVED`/`PREPARING` jobs are also blocked until reconciled.

```sh
python -m scripts.jobs_cli pending
python -m scripts.jobs_cli inspect https://example.com/story
# After independently finding the uploaded video:
python -m scripts.jobs_cli resolve https://example.com/story --published --reference VIDEO_URL --confirm VERIFIED
# Only after verifying that no video was published:
python -m scripts.jobs_cli resolve https://example.com/story --not-published --confirm VERIFIED
```

For Docker, bind-mount a persistent directory and set
`VIDEO_JOBS_DB=/app/data/videonews_jobs.sqlite3`. Back up this file;
losing it can re-enable duplicate uploads. YouTube uploads use
`VIDEO_YOUTUBE_PRIVACY=private` by default; set `public` explicitly
after editorial review. Real external API and cross-machine recovery
testing are still outstanding. The registry prevents duplicates but
is not yet a durable scheduling queue that automatically resumes an
unfinished video render.

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
