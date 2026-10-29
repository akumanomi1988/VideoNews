"""Exercise the MCP stdio handshake and a harmless tool call locally."""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None,
                                reason="Install requirements-mcp.txt to test the MCP transport")


@pytest.mark.asyncio
async def test_stdio_mcp_discovers_tools_and_calls_list_projects(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    environment = os.environ.copy()
    environment["VIDEO_STUDIO_DIR"] = str(tmp_path / "studio")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "scripts.studio_server"],
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"create_project", "save_script", "get_job", "publish_youtube"} <= names
            assert "review_video" in names
            review_tool = next(tool for tool in tools.tools if tool.name == "review_video")
            assert "approve" not in review_tool.inputSchema.get("properties", {})
            result = await session.call_tool("list_projects", {"limit": 1})
            assert not result.isError
            assert result.structuredContent == {"result": []}
