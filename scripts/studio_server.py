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
_studio = VideoNewsStudio()


def call(method: str, **kwargs: Any) -> Any:
    # Legacy providers print progress and debug info. MCP stdio is JSON-RPC only.
    with _stdio_lock, contextlib.redirect_stdout(sys.stderr):
        return getattr(_studio, method)(**kwargs)


@mcp.tool()
def research_news(query: str, language: str = "es", limit: int = 10,
                  country: str = "es", category: str = "") -> dict:
    """Find recent sourced news leads using configured SerpAPI; verify facts independently."""
    return call("research_news", query=query, language=language, limit=limit,
                country=country, category=category)


@mcp.tool()
def retrieve_article(url: str) -> dict:
    """Retrieve bounded source material from a public article URL with redirect checks."""
    return call("retrieve_article", url=url)


@mcp.tool()
def create_script(title: str, source_text: str, source_url: str = "",
                  video_format: str = "short") -> dict:
    """Persist caller-authored narration without making any LLM call."""
    return call("create_script", title=title, source_text=source_text,
                source_url=source_url, video_format=video_format)


@mcp.tool()
def create_project(title: str, video_format: str = "short") -> dict:
    """Create a blank structured project for ChatGPT-authored editorial materials."""
    return call("create_project", title=title, video_format=video_format)


@mcp.tool()
def save_sources(job_id: str, sources: list[dict]) -> dict:
    """Persist source references and retrieval dates; sources remain unverified leads."""
    return call("save_sources", job_id=job_id, sources=sources)


@mcp.tool()
def save_editorial_brief(job_id: str, brief: dict) -> dict:
    """Persist ChatGPT's editorial rationale, risks, angle, format and duration."""
    return call("save_editorial_brief", job_id=job_id, brief=brief)


@mcp.tool()
def save_script(job_id: str, narration: str | list[dict]) -> dict:
    """Persist ChatGPT-authored narration or scene-linked narration segments."""
    return call("save_script", job_id=job_id, narration=narration)


@mcp.tool()
def save_storyboard(job_id: str, scenes: list[dict]) -> dict:
    """Persist ChatGPT-authored scene instructions and visual prompts."""
    return call("save_storyboard", job_id=job_id, scenes=scenes)


@mcp.tool()
def save_youtube_metadata(job_id: str, metadata: dict) -> dict:
    """Persist the reviewed title, description, tags, thumbnail idea and synthetic-media flag."""
    return call("save_youtube_metadata", job_id=job_id, metadata=metadata)


@mcp.tool()
def revise_script(job_id: str, script: str) -> dict:
    """Replace project narration and invalidate obsolete assets/review approval."""
    return call("revise_script", job_id=job_id, script=script)


@mcp.tool()
def generate_images(job_id: str, prompts: list[str] | None = None,
                    count: int = 5, style: str = "PHOTOREALISTIC") -> dict:
    """Optional paid image API mode; disabled unless explicitly enabled in local .env."""
    return call("start_job", action="generate_images", project_id=job_id,
                arguments={"prompts": prompts, "count": count, "style": style})


@mcp.tool()
def import_asset(job_id: str, staged_filename: str, scene_id: str,
                 provenance: dict) -> dict:
    """Import a validated image from output/studio/_imports into a project."""
    return call("import_asset", job_id=job_id, staged_filename=staged_filename,
                scene_id=scene_id, provenance=provenance)


@mcp.tool()
def list_assets(job_id: str) -> list[dict]:
    """List project-scoped assets with source provenance and SHA-256."""
    return call("list_assets", job_id=job_id)


@mcp.tool()
def generate_voice(job_id: str, voice: str = "es-ES-ElviraNeural") -> dict:
    """Narrate with existing Edge TTS, producing audio and word-level SRT timing."""
    return call("start_job", action="generate_voice", project_id=job_id,
                arguments={"voice": voice})


@mcp.tool()
def generate_subtitles(job_id: str, max_words: int = 5) -> dict:
    """Group the existing TTS word-level subtitles using the existing SRT processor."""
    return call("start_job", action="generate_subtitles", project_id=job_id,
                arguments={"max_words": max_words})


@mcp.tool()
def render_video(job_id: str) -> dict:
    """Render locally using existing FFmpeg VideoAssembler; does not publish."""
    return call("start_job", action="render_video", project_id=job_id)


@mcp.tool()
def render_preview(job_id: str) -> dict:
    """Start a 360p preview render for inspection before final rendering."""
    return call("start_job", action="render_preview", project_id=job_id)


@mcp.tool()
def get_job(job_id: str) -> dict:
    """Poll a long-running media job for status and its result or safe error."""
    return call("get_job", job_id=job_id)


@mcp.tool()
def review_video(job_id: str) -> dict:
    """Run read-only artifact checks. Owner upload approval happens in local Windows console."""
    return call("review_video", job_id=job_id)


@mcp.tool()
def publish_youtube(job_id: str) -> dict:
    """Upload PRIVATE only when a local one-use owner authorization exists."""
    return call("publish_youtube", job_id=job_id)


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
