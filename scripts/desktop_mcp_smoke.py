"""Offline MCP smoke test via the exact launcher shipped with the plugin.

Run on Windows: .venv\\Scripts\\python.exe -m scripts.desktop_mcp_smoke
Does not prove ChatGPT Desktop or connect to external APIs.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "chatgpt-plugin" / "server" / "launch.py"
REQUIRED_TOOLS = {
    "studio_status", "research_news", "retrieve_article", "create_project",
    "save_sources", "save_editorial_brief", "save_script", "save_storyboard",
    "save_youtube_metadata", "import_asset", "list_assets", "generate_stock_images", "create_thumbnail", "generate_voice",
    "generate_subtitles", "render_preview", "render_video", "get_job",
    "review_video", "publish_youtube", "get_project", "list_projects",
}


def _result_data(result):
    if result.structuredContent is not None:
        data = result.structuredContent
    elif result.content and getattr(result.content[0], "text", None):
        data = json.loads(result.content[0].text)
    else:
        return None
    while isinstance(data, dict) and isinstance(data.get("result"), (dict, list)):
        data = data["result"]
    return data


async def verify() -> None:
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("VideoNews requires Python 3.11")
    if not LAUNCHER.is_file():
        raise RuntimeError("Packaged launcher missing")
    with tempfile.TemporaryDirectory(prefix="videonews-desktop-mcp-") as tmp:
        env = os.environ.copy()
        env["VIDEONEWS_REPO_PATH"] = str(REPO)
        env["VIDEO_STUDIO_DIR"] = str(Path(tmp) / "studio")
        params = StdioServerParameters(
            command="py" if os.name == "nt" else sys.executable,
            args=["-3.11", str(LAUNCHER)] if os.name == "nt" else [str(LAUNCHER)],
            cwd=str(REPO / "chatgpt-plugin"), env=env,
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=30)) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                schemas={t.name:t.inputSchema for t in (await session.list_tools()).tools}
                if 'configure_audio' not in names or 'bitrate_kbps' not in json.dumps(schemas['configure_audio']):
                    raise RuntimeError('Strict per-project audio contract missing')
                if 'cue_phrases' not in json.dumps(schemas['generate_graphic']):
                    raise RuntimeError('Phrase-anchored graphic contract missing')
                missing = REQUIRED_TOOLS - names
                if missing:
                    raise RuntimeError("Missing MCP tools: " + ", ".join(sorted(missing)))
                status = await session.call_tool("studio_status", {})
                projects = await session.call_tool("list_projects", {"limit": 1})
                if status.isError or projects.isError:
                    raise RuntimeError("MCP read-only calls failed")
                data = _result_data(status)
                if data.get("transport") != "stdio":
                    raise RuntimeError("Invalid Studio transport status")
                if _result_data(projects) != []:
                    raise RuntimeError("Temporary test workspace was not empty")
                # Status/list alone never load the Windows image DLLs that a
                # production call needs. Exercise the first cold image import.
                from PIL import Image, ImageDraw
                inbox = Path(tmp) / "studio" / "_imports"
                image = Image.new("RGB", (64, 36), "navy")
                ImageDraw.Draw(image).rectangle((8, 8, 40, 28), fill="cyan")
                image.save(inbox / "original.png")
                created = _result_data(await session.call_tool("create_project", {
                    "title": "Offline MCP native image dependency acceptance", "video_format": "short"}))
                imported = await session.call_tool("import_asset", {
                    "job_id": created["id"], "staged_filename": "original.png", "scene_id": "smoke",
                    "provenance": {"source": "Original offline smoke-test graphic", "synthetic_media": False}})
                if imported.isError:
                    raise RuntimeError("Cold MCP image dependency/import check failed")
                configured=await session.call_tool('configure_audio',{'job_id':created['id'],
                    'settings':{'equalize':True,'bitrate_kbps':320}})
                if configured.isError:raise RuntimeError('Per-project audio tool failed')
                await session.call_tool('save_sources',{'job_id':created['id'],'sources':[{
                    'title':'Controlled offline fixture','url':'https://example.org/fixture',
                    'publisher':'Test fixture','published_at':'','summary':'Not a real news claim'}]})
                await session.call_tool('save_storyboard',{'job_id':created['id'],'scenes':[{
                    'id':'smoke','narration':'Controlled test narration.','visual_prompt':'Original offline test graphic'}]})
                generated=await session.call_tool('generate_graphic',{'job_id':created['id'],'scene_id':'smoke',
                    'specification':{'kind':'fact_card','title':'Offline graphic','aspect_ratio':'9:16',
                        'items':[{'label':'Controlled test graphic','source_url':'https://example.org/fixture'}]}})
                if generated.isError:raise RuntimeError('Native graphic MCP call failed')
                task=_result_data(generated)
                async with asyncio.timeout(30):
                    while True:
                        await asyncio.sleep(.1)
                        response=await session.call_tool('get_job',{'job_id':task['job_id']})
                        job=response.structuredContent or json.loads(response.content[0].text)
                        if 'status' not in job:job=job['result']
                        if job['status'] in ('succeeded','failed'):break
                if job['status']!='succeeded':raise RuntimeError(str(job))
                print(f"PASS: packaged launcher, MCP handshake, {len(names)} tools, status, list_projects and cold image import")
                print('PASS: strict configure_audio and asynchronous source-bound generate_graphic over MCP')
                print("ChatGPT Desktop app connection remains a separate acceptance test.")
    # Let Windows Proactor transports finish closing before asyncio shuts down.
    await asyncio.sleep(.5)


if __name__ == "__main__":
    asyncio.run(verify())
