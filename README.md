# VideoNews AI Studio

VideoNews is a Windows-first news video production engine for NewSphere. The
primary workflow is operated through ChatGPT connected to the local Python
engine over a private MCP connection. ChatGPT performs research synthesis,
editorial selection, fact checking, narration, storyboards, and YouTube metadata.
Python validates and stores those artifacts, retrieves source material,
processes assets, creates speech and subtitles, renders video, and uploads only
after a separate owner approval from the local Windows console.

The Studio workflow does not make Python LLM calls to rewrite ChatGPT scripts.
An optional CLI fallback can use configured automated providers. ChatGPT Plus
does not provide an OpenAI API key or free API image/audio usage.

## ChatGPT Desktop — local MCP

The private **VideoNews AI Studio** plugin includes a local stdio MCP launcher. For the Windows workflow, install Python 3.11 and FFmpeg and run from PowerShell at the repository root:

```powershell
.\bootstrap.ps1
.\scripts\setup_desktop_mcp.ps1
```

The bootstrap now installs the MCP SDK. The setup script sets `VIDEONEWS_REPO_PATH` for the Windows user and verifies the packaged launcher with a harmless MCP initialization, tool discovery, `studio_status` and `list_projects` call in an isolated temporary workspace. It does not call news APIs or publish videos.

**Completely restart ChatGPT Desktop** so it inherits the environment variable, install/update the private VideoNews AI Studio plugin, and start a **Work locally** conversation. Ask it to call `studio_status` and `list_projects`. Only a real call from ChatGPT Desktop proves the plugin works in the Desktop host.

The local MCP server is not available to web/mobile/cloud Chat without a separate authenticated connection. ChatGPT-generated images still require manual staging in `output/studio/_imports`; Google OAuth credentials must be valid for YouTube uploading. See `docs/CHATGPT_STUDIO.md`.

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
for live discovery. Edge TTS uses a network service. Azure image generation is
paid and disabled in the ChatGPT Studio unless
`VIDEO_ENABLE_PAID_IMAGE_GENERATION=true` is set explicitly.

## ChatGPT workflow

The MCP provides tools for sourced news retrieval, article extraction,
structured project creation, scripts/storyboards/metadata persistence, validated
asset import, speech, subtitles, preview and final rendering, project/job
inspection, read-only quality review, and private YouTube publishing.

Long media operations return job IDs; poll `get_job`. Images generated or
reviewed inside ChatGPT must be transferred manually to
`output/studio/_imports` before importing. Python does not have automatic access
to ChatGPT image-generation outputs.

Run `.\.venv\Scripts\python.exe -m scripts.owner_authorize_upload PROJECT_ID`
only after inspecting the rendered file locally. This interactive action binds a
single-use, expiring grant to the exact video hash, OAuth channel, private
privacy status, and YouTube upload operation. MCP cannot issue that grant.
Unknown upload outcomes require manual reconciliation and are never retried.

See [docs/CHATGPT_STUDIO.md](docs/CHATGPT_STUDIO.md) for project schema,
workflow details, Secure MCP Tunnel setup, account permissions, asset provenance,
and publishing safeguards.

## Secure ChatGPT connection

The repository server currently runs over local MCP stdio. Connecting ChatGPT
requires OpenAI Secure MCP Tunnel, a `tunnel_id`, a restricted runtime API key,
Platform Tunnels Read + Use permissions, and permission to add custom MCP servers
in the target ChatGPT workspace. Creating/managing a tunnel also requires
Platform Tunnels Read + Manage. Do not expose the local server on an
unauthenticated public endpoint.

The current checkout has not proven a live ChatGPT call: `tunnel-client` and
account permission visibility were unavailable in the checked environment.
Install `mcp` with `requirements-mcp.txt`, complete the tunnel/account steps,
and verify a real call before calling the integration complete.

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
