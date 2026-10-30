"""Exercise the MCP stdio handshake and a harmless tool call locally."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None,
                                reason="Install requirements-mcp.txt to test the MCP transport")


@pytest.mark.asyncio
async def test_stdio_mcp_discovers_tools_and_calls_list_projects(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    environment = os.environ.copy()
    environment["VIDEO_STUDIO_DIR"] = str(tmp_path / "studio")
    environment["VIDEO_PUBLISH_POLICY_DIR"] = str(tmp_path / "publish-policy")
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
            assert {"create_project", "save_script", "get_job", "create_thumbnail",
                    "generate_stock_images", "publish_youtube", "studio_status"} <= names
            assert "review_video" in names
            publish_tool = next(tool for tool in tools.tools if tool.name == "publish_youtube")
            publish_schema = json.dumps(publish_tool.inputSchema)
            assert all(f'"{mode}"' in publish_schema
                       for mode in ("public", "private", "unlisted"))
            review_tool = next(tool for tool in tools.tools if tool.name == "review_video")
            assert "approve" not in review_tool.inputSchema.get("properties", {})
            brief_tool = next(tool for tool in tools.tools if tool.name == "save_editorial_brief")
            brief_schema = brief_tool.inputSchema["$defs"]["EditorialBrief"]
            packaged_brief_schema = json.loads(
                (Path(__file__).parents[1] / "chatgpt-plugin" / "schemas" /
                 "editorial-brief.schema.json").read_text(encoding="utf-8"))
            assert brief_schema["properties"] == packaged_brief_schema["properties"]
            assert brief_schema["required"] == packaged_brief_schema["required"]
            assert brief_schema["additionalProperties"] is False
            for definition, schema in packaged_brief_schema["$defs"].items():
                assert brief_tool.inputSchema["$defs"][definition] == schema
            assert brief_schema["additionalProperties"] is False
            assert set(brief_schema["required"]) >= {
                "selection_mode", "selected_story", "alternatives", "verified_sources",
                "format", "aspect_ratio", "target_duration_seconds", "visual_strategy",
                "destination", "privacy_status", "approval_status",
            }
            result = await session.call_tool("list_projects", {"limit": 1})
            assert not result.isError
            projects = result.structuredContent
            if projects is None:
                projects = json.loads(result.content[0].text)
            while isinstance(projects, dict) and isinstance(projects.get("result"), list):
                projects = projects["result"]
            assert projects == []
            status = await session.call_tool("studio_status", {})
            assert not status.isError
            readiness = status.structuredContent
            if readiness is None:
                readiness = json.loads(status.content[0].text)
            while isinstance(readiness, dict) and isinstance(readiness.get("result"), dict):
                readiness = readiness["result"]
            assert readiness.get("transport") == "stdio"
            assert readiness.get("publishing_policy") == "owner_enrollment_required"
            assert readiness.get("publishing_default_privacy") is None
            assert "youtube_client_secrets_present" in readiness
