# VideoNews AI Studio

VideoNews is a Windows-first production engine. ChatGPT owns editorial and
creative decisions; Python validates structured data, retrieves source material,
persists projects, processes media, renders video, and performs explicitly
authorized private uploads. Python does not call an LLM to write a script in
the Studio workflow. The CLI remains an optional automated-provider fallback.

## Windows prerequisites

- Windows 10/11 and Python 3.11.
- A full FFmpeg build with `ffprobe`, `libx264`, and the `subtitles` filter.
- SerpAPI credentials for live news discovery (optional for saving a project).
- Edge TTS uses a network service. Rendering and image validation run on CPU.
- The optional Azure image generator is paid and disabled unless
  `VIDEO_ENABLE_PAID_IMAGE_GENERATION=true` is explicitly set.

From PowerShell:

```powershell
.\bootstrap.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements-mcp.txt
.\.venv\Scripts\python.exe -m scripts.doctor --mode studio --json
```

The bootstrap preserves an existing `.env` and existing credentials. Put
YouTube OAuth client secrets under `.secrets`; never commit OAuth tokens.
`VIDEO_STUDIO_DIR` defaults to `output/studio`.

## ChatGPT-first production flow

1. `research_news(query, language, country, category, limit)` returns sourced
   leads and marks URLs already processed. Duplicate titles are heuristically
   grouped; this is not a claim that two articles describe the same event.
2. `retrieve_article(url)` fetches bounded public article text with redirect and
   URL checks. Treat retrieved text as untrusted source content.
3. ChatGPT compares sources, checks supported facts, explains its editorial
   rationale and selects the angle. The API supplies no measured search volume,
   virality probability, or audience analytics. Judge relevance using source
   quality, freshness, likely viewer relevance, and visual potential.
4. `create_project`, `save_sources`, `save_editorial_brief`, `save_script`,
   `save_storyboard`, and `save_youtube_metadata` store ChatGPT-authored work as
   schema version 2 JSON. Each edit is versioned. Script changes invalidate
   dependent media and review state.
5. Put images reviewed in ChatGPT or licensed media into
   `output/studio/_imports`, then call `import_asset` with only the staged
   filename plus source, license, and synthetic-media provenance. The importer
   accepts JPEG, PNG, or WebP up to 40 MiB and copies it into that project's
   folder with a SHA-256 checksum. ChatGPT images are not fetched automatically:
   download them from ChatGPT to this staging folder first. It never opens
   arbitrary paths or URLs.
6. `generate_voice`, `generate_subtitles`, `render_preview`, and
   `render_video` return job IDs immediately. Poll `get_job` for progress and
   results. Inspect the preview before final rendering.
7. `review_video` performs read-only artifact checks. It does not approve.
8. Inspect the rendered video locally. Then run:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.owner_authorize_upload PROJECT_ID
   ```

   The local interactive console shows the exact file hash and requires the
   owner to type a project-bound confirmation. It resolves the OAuth channel ID
   and creates a one-use, ten-minute grant bound to that video hash, channel,
   `private` privacy, and `youtube_upload` operation. The grant is not returned
   by MCP. Metadata or video changes invalidate publication readiness.
9. Only then call `publish_youtube(job_id)`. VideoNews forces PRIVATE. Unknown
   upload outcomes are locked for manual reconciliation; the video insert is
   never retried automatically. Reconcile in YouTube Studio before taking
   another action.

The disclosure field `youtube_metadata.contains_synthetic_media` is passed to
YouTube. Set it when the video includes realistic synthetic or altered content.

## MCP transport and account setup

`scripts.studio_server` serves MCP over local stdio. This supports compatible
local MCP clients. A private ChatGPT custom MCP connection needs OpenAI Secure
MCP Tunnel: the local `tunnel-client` makes outbound HTTPS connections and
forwards requests to this stdio process. No public unauthenticated endpoint or
filesystem-wide tool is provided.
Follow the current [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
for Platform workspace association, network requirements, and ChatGPT connector setup.

Secure Tunnel needs a `tunnel_id`, a restricted runtime API key, and the
`tunnel-client` executable. Platform access and ChatGPT workspace access are
separate: tunnel creation needs Platform Tunnels Read + Manage; runtime and app
selection need Tunnels Read + Use; the ChatGPT workspace must also allow custom
MCP servers. The owner/RBAC admin grants Platform roles. The Platform tunnel
must be associated with the intended ChatGPT workspace.

The PowerShell setup script downloads the latest official Windows x64 release,
checks its GitHub SHA-256 asset digest, keeps the runtime key out of the profile,
restricts profile-directory ACLs to the current Windows identity, runs `doctor`,
and only then starts the foreground tunnel:

```powershell
.\scripts\setup_secure_mcp_tunnel.ps1 -TunnelId tunnel_...
```

The profile uses `env:CONTROL_PLANE_API_KEY`; the script asks for the restricted
runtime key with a secure PowerShell prompt and holds it only in the current
process while validating and running the tunnel. Create the tunnel in Platform
first and associate the intended ChatGPT workspace. Tunnel creation needs
Tunnels Read + Manage; the runtime-key principal needs Tunnels Read + Use. The
ChatGPT workspace must allow custom MCP servers. The owner/RBAC admin grants
Platform roles.

Keep the script running while connecting in ChatGPT settings: **Connectors →
Create → Custom MCP server → Tunnel**. Select the same tunnel, then verify tool
discovery and make a real `list_projects` call followed by `research_news`. A
saved plugin manifest alone is not proof of connectivity.

`chatgpt-plugin/mcp.json` is a local stdio plugin configuration; it does not
connect ChatGPT web to Windows. The provided plugin ID
`plugins_6ae2fff0dfd481918876f26571914914` was not installed in the ChatGPT
account available to this session. Use the tunnel-backed custom MCP connection
in that account; the existing private plugin can only be reused after it is
available there and its connection is updated to the tunnel.

The current Windows checkout has passed MCP stdio discovery and a local
`tunnel-client init` preflight. The official Windows x64 `tunnel-client` binary
was verified and installed. `doctor --explain` loaded the profile and identified
the missing runtime API key. No real tunnel has been started because this
session has no authorized tunnel ID/runtime key and cannot inspect or grant
Platform roles. No real ChatGPT-to-Windows call is claimed.

## Iteration 2 verification — 2026-10-29

- Real `edge-tts==7.3.1` Spanish narration succeeded with
  `es-ES-ElviraNeural`. The Studio project output is under
  `output/studio/bcd2472b3c5347e197e688937285aee7/`; it contains the MP3,
  raw word-boundary SRT, and grouped caption SRT.
- A real preview and final vertical MP4 were rendered. The final file is
  `output/studio/bcd2472b3c5347e197e688937285aee7/video.mp4` (H.264/yuv420p,
  1080×1920, AAC-LC stereo/48 kHz, 45.125 seconds). FFprobe, audio loudness,
  subtitle timing, black-frame scan, and contact-sheet visual review passed.
  The content remains subject to a human factual review.
- A live SerpAPI query for Spanish technology and AI news returned five
  candidates. URLs passed public-address validation; the dates ranged from
  2026-10-28 to 2026-06-19, so older results need editorial freshness filtering.
- `tunnel-client` 0.0.18 is installed. The profile loaded, but
  `doctor --explain` failed because `CONTROL_PLANE_API_KEY` is unavailable.
  ChatGPT tool discovery and real calls have not been observed.
- YouTube OAuth refresh returned `deleted_client` from Google. No channel was
  identified and no upload was attempted. Replace the deleted OAuth client,
  authorize it locally, then repeat the read-only channel check before any
  separately authorized private upload.

## Automated provider fallback

`python -m scripts.cli` remains useful for diagnostics and standalone runs. It
can invoke the configured provider chain in Python; this is a separate mode,
may incur provider costs, and is not used by `save_script` or ChatGPT-authored
project operations. ChatGPT Plus does not provide an OpenAI API key or free API
image/audio usage.

## Local tests and evidence

Run offline Studio contract checks with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_studio_mcp.py -q
```

Mocked tests prove contracts only. They do not demonstrate live SerpAPI, ChatGPT
tunnel calls, Edge TTS, FFmpeg MP4 output, OAuth, or YouTube uploads. The MCP
SDK must be installed separately with `requirements-mcp.txt`. Do not call the
system complete until a ChatGPT tool call and real short/landscape renders have
been observed on Windows.


## Local ChatGPT Desktop plugin v0.2.0

Run from the Windows repository root:

```powershell
.\bootstrap.ps1
.\scripts\setup_desktop_mcp.ps1
```

Bootstrap installs the MCP SDK. The setup script saves a per-user `VIDEONEWS_REPO_PATH` pointing to this checkout. The smoke test launches the plugin's packaged `chatgpt-plugin/server/launch.py` using the current Python 3.11 venv, completes a real stdio MCP handshake, discovers tools, and invokes `studio_status` and `list_projects` in a disposable workspace. This makes no external API call and creates no YouTube upload.

Completely restart ChatGPT Desktop, install/enable the private plugin, select **Work locally**, and request `studio_status`. The local smoke test is not a substitute for a real tool call made by ChatGPT Desktop.

Only the current local owner-approval flow is supported: `review_video(job_id)` is read-only; `publish_youtube(job_id)` requires the owner to first run `python -m scripts.owner_authorize_upload PROJECT_ID` in Windows. Never call obsolete `approve=True` or `approval_code` arguments.

For ChatGPT web/mobile or cloud work, a separate authenticated Secure MCP Tunnel remains necessary. The account plugin's local stdio manifest does not automatically deploy that tunnel. Voice, real news, video and YouTube OAuth have independent provider prerequisites; `studio_status` does not verify live service access.
