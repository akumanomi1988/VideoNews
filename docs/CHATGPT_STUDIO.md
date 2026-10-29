# VideoNews AI Studio (private local MCP plugin)

This adapter reuses the existing Python 3.11 engine (SerpAPIProvider, Chatbot,
FluxImageGenerator, TTSEdge, SRTProcessor, VideoAssembler and YoutubeMediaUploader).
Telegram and CLI continue to operate.

## Safety boundaries

- Default output is local, not automatic publishing.
- MCP publishing always uses YouTube PRIVATE, regardless of environment values.
- Publication requires rendered media and an explicit editorial approval via
  review_video(job_id, approve=True), returning a single-use approval code.
- The code is verified against the rendered file SHA-256 at publishing time.
- Every attempted upload persists status=uploading first. An uncertain failure
  persists upload_unknown: NEVER retry automatically. Reconcile via YouTube Studio.
- A valid source link is required for editorial review. The agent cannot verify
  accuracy or image rights automatically; a person must check script, claims,
  context, sources and imagery before approval.
- Project state is local JSON written atomically under output/studio/<job_id>.
- Never put secrets in news text, prompts or source control. The GitHub repo is
  currently public; private plugin visibility is independent from repository visibility.
- The server has filesystem and publishing powers. Never expose it on a public
  HTTP endpoint without authentication, authorization and audit controls.

## Windows 10/11 installation

From the cloned repository in PowerShell (Python 3.11, FFmpeg required):

    .\bootstrap.ps1
    .\.venv\Scripts\python.exe -m pip install "mcp>=1.18,<2"
    .\.venv\Scripts\python.exe -m scripts.doctor --mode cli --json
    .\.venv\Scripts\python.exe -m pytest tests/test_studio_mcp.py -q
    .\.venv\Scripts\python.exe -m scripts.studio_server

If bootstrap created a venv with another name, use that interpreter.
The final process speaks MCP over stdio, not HTTP: do not type into it.
A compatible local MCP client launches it automatically. When using
the private plugin launcher, set VIDEONEWS_REPO_PATH to the absolute
Windows path of the cloned repository.

The existing provider configuration uses SERPAPI_API_KEY, OLLAMA_URL or
GROQ_API_KEY, AZURE_IMAGE_ENDPOINT and AZURE_IMAGE_API_KEY.
The current image generator requires Azure; no imaginary local image backend.
The current voice integration uses Edge TTS.

Put Google installed-app OAuth secrets under .secrets/client_secret.json
(or set YOUTUBE_CLIENT_SECRETS_FILE). The existing uploader opens a browser
for initial OAuth consent and stores tokens in .secrets.
The uploader publishes to the account authorized by those credentials.

## ChatGPT tool workflow

1. research_news(query): discover news leads with original URLs.
2. create_script(title, source_text, source_url, video_format): persistent draft.
3. revise_script(job_id, script): correct text (invalidates obsolete media).
4. generate_images(job_id, count, style): produce images; optional custom prompts.
5. generate_voice(job_id, voice): Edge narration + word-boundary SRT.
6. generate_subtitles(job_id, max_words): group synchronized captions.
7. render_video(job_id): local FFmpeg MP4 without uploading.
8. review_video(job_id): inspect duration, sources and required artifacts.
9. After explicit human editorial approval, review_video(job_id, approve=True)
   produces the one-time approval code.
10. publish_youtube(job_id, approval_code): upload PRIVATE.
11. get_project and list_projects: inspect current state.

The operator must independently fact-check original source material.
Generated visuals must not be presented as real photojournalism.

## ChatGPT transport limits

This package configures a Windows LOCAL stdio MCP process. Saving a private
plugin in ChatGPT does not grant ChatGPT web/mobile direct execution access
to Windows applications.

To run it from ChatGPT web, a separate securely authenticated remote MCP
gateway/tunnel is required. This is deliberately NOT exposed automatically,
because local files and YouTube account credentials must remain protected.
The supplied server is usable from compatible local MCP clients.

## Verification

    .\.venv\Scripts\python.exe -m pytest tests/test_studio_mcp.py -q

These tests mock external services. They do not prove end-to-end Azure,
FFmpeg, OAuth or YouTube execution. Verify those with a manually reviewed
private upload on Windows.
