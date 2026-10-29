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
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
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
                print(f"PASS: packaged launcher, MCP handshake, {len(names)} tools, status and list_projects")
                print("ChatGPT Desktop app connection remains a separate acceptance test.")


if __name__ == "__main__":
    asyncio.run(verify())
