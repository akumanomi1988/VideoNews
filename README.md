# VideoNews AI Studio

VideoNews is a Windows-first news video production engine for NewSphere. The
primary workflow is operated through ChatGPT connected to the local Python
engine over a private MCP connection. ChatGPT performs research synthesis,
editorial selection, fact checking, narration, storyboards, and YouTube metadata.
Python validates and stores those artifacts, retrieves source material,
processes licensed assets, creates speech and subtitles, renders video, and
uploads under a local visibility policy explicitly enrolled by the owner.

The Studio workflow does not make Python LLM calls to rewrite ChatGPT scripts.
An optional CLI fallback can use configured automated providers. ChatGPT Plus
does not provide an OpenAI API key or free API image/audio usage.

## ChatGPT Desktop — local MCP

The private **VideoNews AI Studio** plugin includes a local stdio MCP launcher. For the Windows workflow, install Python 3.11 and FFmpeg and run from PowerShell at the repository root:

```powershell
.\bootstrap.ps1
```

The bootstrap installs the MCP SDK, sets `VIDEONEWS_REPO_PATH` for the Windows user, and verifies the packaged launcher with a harmless MCP initialization, tool discovery, `studio_status` and `list_projects` call in an isolated temporary workspace. It does not call news APIs or publish videos. Rerun `scripts\\setup_desktop_mcp.ps1` when only the local MCP setup needs repair.

**Completely restart ChatGPT Desktop** so it inherits the environment variable, install/update the private VideoNews AI Studio plugin, and start a **Work locally** conversation. Ask it to call `studio_status` and `list_projects`. Only a real call from ChatGPT Desktop proves the plugin works in the Desktop host.

Local MCP is available to compatible Desktop **Work locally** conversations;
web/mobile/cloud Chat requires a separate authenticated Secure MCP Tunnel.
NewSphere Cinematic uses Azure MAI generated illustrations as its primary
visual source when `VIDEO_ENABLE_PAID_IMAGE_GENERATION=true` and Azure
credentials are configured. Pexels is secondary and runs only when explicitly
selected in the approved project brief; it is never an automatic fallback.
See `docs/CHATGPT_STUDIO.md`.

## Windows setup

Requirements: Windows 10/11, Python 3.11, and a full FFmpeg build containing
`ffprobe`, `libx264`, and the `subtitles` filter. No GPU is required.

```powershell
winget install -e --id Python.Python.3.11
winget install -e --id Gyan.FFmpeg
git clone https://github.com/akumanomi1988/VideoNews.git
cd VideoNews
.\bootstrap.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
notepad .env
```

Bootstrap preserves an existing `.env` and secrets. Configure `SERPAPI_API_KEY`
for live discovery. Edge TTS uses a network service. The example configuration
enables Azure image generation (`MEDIA_SOURCE=huggingface` is the compatibility
alias for Azure MAI); valid Azure endpoint and key values are still required.
Azure image requests may incur charges. Turn generation off by setting
`VIDEO_ENABLE_PAID_IMAGE_GENERATION=false`.

## ChatGPT workflow

The MCP provides sourced news retrieval, project/script/storyboard persistence,
scene-matched Azure MAI illustrations, validated asset import, Spanish
narration, subtitles, preview and final rendering, read-only quality review,
and owner-configured YouTube publishing. Licensed Pexels images are available
only when explicitly selected in the approved brief; image-generation failure
does not silently switch providers.

Long media operations return job IDs; poll `get_job`. `generate_stock_images`
uses the configured Pexels key only after explicit stock selection and stores
provider, license and photographer credits per scene. ChatGPT-generated images remain a manual import option;
there is no silent ChatGPT image export API.

One-time owner enrollment is available through
`.\.venv\Scripts\python.exe -m scripts.owner_publish_policy enroll`; it verifies
the OAuth channel is NewSphere and stores a user-only privacy policy with a
daily limit of up to 100 uploads per UTC day. New enrollment defaults to
`private`; public or unlisted uploads require explicit owner consent when
enrolling those modes. `--privacy-status`
selects another enrolled default, and `--allow-privacy-status` can authorize
additional per-video choices. After
enrollment, an explicit conversational request can call `publish_youtube`
without another per-video console command. YouTube Data API read-back verifies
the resulting channel and visibility. The stricter
`owner_authorize_upload.py` flow provides an exact-file one-use grant, defaults
to private and requires local confirmation of project and SHA-256 for public.
Unknown upload outcomes require reconciliation and are never retried.

See [docs/CHATGPT_STUDIO.md](docs/CHATGPT_STUDIO.md) for project schema,
workflow details, Secure MCP Tunnel setup, account permissions, asset provenance,
and publishing safeguards.

## Secure ChatGPT connection

The local Desktop mode uses the private plugin's stdio launcher from a ChatGPT
**Work locally** conversation. A normal cloud Chat connection requires Secure
MCP Tunnel, Platform Tunnels Read + Use, and workspace permission to add custom
MCP servers; tunnel management also requires Tunnels Read + Manage. Do not
expose the local server on an unauthenticated public endpoint. A stdio smoke
test does not prove a ChatGPT-hosted tool call.

## Local diagnostics and tests

```powershell
.\.venv\Scripts\python.exe -m scripts.doctor --mode studio --json
.\.venv\Scripts\python.exe -m pytest tests\test_studio_mcp.py -q
```

To use the standalone automated-provider fallback, set provider credentials in
`.env` and run `python -m scripts.cli --title "A sourced news headline" --format short`.
This fallback may incur external costs. Keep upload disabled while testing.

## Safety and evidence

News results are source leads, not verified facts or audience analytics. Check
original sources, dates, claims, copyright, image provenance, subtitles, and
audio/video synchronization before upload. The tests mock external systems;
they are not evidence of live SerpAPI, ChatGPT tunnel, FFmpeg renders, OAuth, or
YouTube operation. The system is not complete until ChatGPT connectivity and
real vertical and landscape renders have been verified on Windows.
