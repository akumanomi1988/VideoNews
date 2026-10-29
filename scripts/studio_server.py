"""stdio MCP entry point for VideoNews AI Studio (Windows Python 3.11).

Run from the repository root: py -3.11 -m scripts.studio_server
All legacy print() output is redirected to stderr to protect JSON-RPC stdout.
"""
from __future__ import annotations

import contextlib
import sys
import threading
from typing import Any

from mcp.server.fastmcp import FastMCP

from scripts.studio_mcp import VideoNewsStudio

mcp = FastMCP("VideoNews AI Studio")
_stdio_lock = threading.RLock()


def call(method: str, **kwargs: Any) -> Any:
    # Legacy providers print progress and debug info. MCP stdio is JSON-RPC only.
    with _stdio_lock, contextlib.redirect_stdout(sys.stderr):
        return getattr(VideoNewsStudio(), method)(**kwargs)


@mcp.tool()
def research_news(query: str, language: str = "es", limit: int = 10) -> dict:
    """Find recent sourced news leads using configured SerpAPI; verify facts independently."""
    return call("research_news", query=query, language=language, limit=limit)


@mcp.tool()
def create_script(title: str, source_text: str, source_url: str = "",
                  video_format: str = "short") -> dict:
    """Create an editable Spanish news narration and a persistent project. Requires source facts."""
    return call("create_script", title=title, source_text=source_text,
                source_url=source_url, video_format=video_format)


@mcp.tool()
def revise_script(job_id: str, script: str) -> dict:
    """Replace project narration and invalidate obsolete assets/review approval."""
    return call("revise_script", job_id=job_id, script=script)


@mcp.tool()
def generate_images(job_id: str, prompts: list[str] | None = None,
                    count: int = 5, style: str = "PHOTOREALISTIC") -> dict:
    """Generate and preserve image files with the existing Azure image generator."""
    return call("generate_images", job_id=job_id, prompts=prompts, count=count, style=style)


@mcp.tool()
def generate_voice(job_id: str, voice: str = "es-ES-ElviraNeural") -> dict:
    """Narrate with existing Edge TTS, producing audio and word-level SRT timing."""
    return call("generate_voice", job_id=job_id, voice=voice)


@mcp.tool()
def generate_subtitles(job_id: str, max_words: int = 5) -> dict:
    """Group the existing TTS word-level subtitles using the existing SRT processor."""
    return call("generate_subtitles", job_id=job_id, max_words=max_words)


@mcp.tool()
def render_video(job_id: str) -> dict:
    """Render locally using existing FFmpeg VideoAssembler; does not publish."""
    return call("render_video", job_id=job_id)


@mcp.tool()
def review_video(job_id: str, approve: bool = False) -> dict:
    """Inspect artifacts. Only approve=True after explicit human editorial approval issues a code."""
    return call("review_video", job_id=job_id, approve=approve)


@mcp.tool()
def publish_youtube(job_id: str, approval_code: str) -> dict:
    """Upload to YouTube PRIVATE only after editorial approval; never auto-retry unknown uploads."""
    return call("publish_youtube", job_id=job_id, approval_code=approval_code)


@mcp.tool()
def get_project(job_id: str) -> dict:
    """Inspect current project state and artifact paths without reading credentials."""
    return call("get_project", job_id=job_id)


@mcp.tool()
def list_projects(limit: int = 20) -> list[dict]:
    """List recent local projects and publishing states."""
    return call("list_projects", limit=limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
