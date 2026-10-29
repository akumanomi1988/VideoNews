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
   folder with a SHA-256 checksum. It never opens arbitrary paths or URLs.
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

Secure Tunnel needs a `tunnel_id`, a restricted runtime API key, and the
`tunnel-client` executable. Platform access and ChatGPT workspace access are
separate: tunnel creation needs Platform Tunnels Read + Manage; runtime and app
selection need Tunnels Read + Use; the ChatGPT workspace must also allow custom
MCP servers. The owner/RBAC admin grants Platform roles. The Platform tunnel
must be associated with the intended ChatGPT workspace.

Follow the current [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels):

1. Download `tunnel-client` from Platform tunnel settings or the official
   [OpenAI tunnel-client releases](https://github.com/openai/tunnel-client/releases).
2. Create/reuse the private tunnel in Platform and associate the ChatGPT
   workspace. Enter the runtime key locally; do not place it in chat, source
   control, command history, or logs.
3. Configure a stdio profile with `--mcp-command` pointing to
   `\.venv\Scripts\python.exe -m scripts.studio_server` from the repository
   root. Run `tunnel-client doctor --profile PROFILE --explain`, then
   `tunnel-client run --profile PROFILE`.
4. In ChatGPT Plugins, choose **Add custom MCP server**, **Tunnel**, then select
   the same tunnel. Confirm the app risk warning and enable the VideoNews tools.
5. Verify discovery and run `list_projects` or a harmless `research_news` call.
   A saved plugin manifest alone is not proof of connectivity.

The current Windows checkout has the MCP SDK installed and has passed local
stdio discovery/call checks. It has not completed the account steps: no
`tunnel-client` is installed, and this session cannot inspect Platform tunnel
roles or ChatGPT workspace permissions. Therefore no real ChatGPT-to-Windows
call is claimed. Obtain the account permissions, configure the tunnel, and
record a successful ChatGPT tool call to complete this checkpoint.

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
