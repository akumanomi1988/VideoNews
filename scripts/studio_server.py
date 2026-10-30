"""stdio MCP entry point for VideoNews AI Studio (Windows Python 3.11).

Run from the repository root: py -3.11 -m scripts.studio_server
All legacy print() output is redirected to stderr to protect JSON-RPC stdout.
"""
from __future__ import annotations

import contextlib
import sys
import threading
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from scripts.studio_mcp import VideoNewsStudio

mcp = FastMCP("VideoNews AI Studio")
_stdio_lock = threading.RLock()
_studio = VideoNewsStudio()


class _StrictBriefModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BriefStory(_StrictBriefModel):
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=3000)
    primary_url: str = Field(min_length=8, max_length=2000, pattern=r"^https://")
    why_selected: str = Field(min_length=1, max_length=2000)


class BriefAlternative(_StrictBriefModel):
    title: str = Field(min_length=1, max_length=500)
    primary_url: str = Field(min_length=8, max_length=2000, pattern=r"^https://")
    reason: str = Field(min_length=1, max_length=2000)


class BriefSource(_StrictBriefModel):
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=8, max_length=2000, pattern=r"^https://")
    publisher: str = Field(min_length=1, max_length=200)
    published_at: str = Field(max_length=100)
    supports: str = Field(min_length=1, max_length=3000)


class EditorialBrief(_StrictBriefModel):
    selection_mode: Literal["manual", "delegated"]
    selected_story: BriefStory
    alternatives: list[BriefAlternative] = Field(max_length=20)
    verified_sources: list[BriefSource] = Field(min_length=1, max_length=30)
    format: Literal["short", "long"]
    aspect_ratio: Literal["9:16", "16:9"]
    target_duration_seconds: int = Field(ge=10, le=3600)
    editorial_angle: str = Field(min_length=1, max_length=2000)
    tone: str = Field(min_length=1, max_length=2000)
    target_audience: str = Field(min_length=1, max_length=2000)
    language: str = Field(min_length=1, max_length=2000)
    narrative_concept: str = Field(min_length=1, max_length=2000)
    opening_hook: str = Field(min_length=1, max_length=2000)
    visual_strategy: str = Field(min_length=1, max_length=2000)
    image_sources: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(min_length=1, max_length=20)
    destination: Literal["NewSphere"]
    privacy_status: Literal["public", "private", "unlisted"]
    approval_status: Literal["proposed", "approved"]
    duration_tolerance_seconds: int = Field(ge=3, le=300)


def call(method: str, **kwargs: Any) -> Any:
    # Legacy providers print progress and debug info. MCP stdio is JSON-RPC only.
    with _stdio_lock, contextlib.redirect_stdout(sys.stderr):
        return getattr(_studio, method)(**kwargs)


@mcp.tool()
def research_news(query: str, language: str = "es", limit: int = 10,
                  country: str = "es", category: str = "") -> dict:
    """Return recent source leads with freshness, duplicate, and local-project match heuristics."""
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
def create_project(title: str, video_format: Literal["short", "long"] = "short") -> dict:
    """Create a blank structured project for ChatGPT-authored editorial materials."""
    return call("create_project", title=title, video_format=video_format)


@mcp.tool()
def save_sources(job_id: str, sources: list[dict]) -> dict:
    """Persist source references and retrieval dates; sources remain unverified leads."""
    return call("save_sources", job_id=job_id, sources=sources)


@mcp.tool()
def save_editorial_brief(job_id: str, brief: EditorialBrief) -> dict:
    """Persist strict, versioned editorial decisions; content changes reset approval to proposed."""
    return call("save_editorial_brief", job_id=job_id, brief=brief.model_dump())


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
                    count: int | None = None, style: str = "NEWSPHERE_CINEMATIC") -> dict:
    """Generate and persist one original cinematic AI visual per missing storyboard scene; never falls back to stock."""
    return call("start_job", action="generate_images", project_id=job_id,
                arguments={"prompts": prompts, "count": count, "style": style})


@mcp.tool()
def generate_stock_images(job_id: str) -> dict:
    """Explicitly fetch licensed Pexels visuals for a project that selected stock as its source."""
    return call("start_job", action="generate_stock_images", project_id=job_id)


@mcp.tool()
def create_thumbnail(job_id: str) -> dict:
    """Create a validated NewSphere thumbnail asynchronously from project visuals and metadata."""
    return call("start_job", action="create_thumbnail", project_id=job_id)


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
    """Render the approved brief using FFmpeg and verify actual duration, resolution, and streams."""
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
    """Compare the final artifact with its approved brief; report blocking technical/editorial issues."""
    return call("review_video", job_id=job_id)


@mcp.tool()
def publish_youtube(job_id: str,
                    privacy_status: Literal["public", "private", "unlisted"] | None = None) -> dict:
    """Publish only after brief QA and matching local owner authorization; verify effective YouTube status."""
    return call("publish_youtube", job_id=job_id, privacy_status=privacy_status)


@mcp.tool()
def get_project(job_id: str) -> dict:
    """Inspect current project state and artifact paths without reading credentials."""
    return call("get_project", job_id=job_id)


@mcp.tool()
def studio_status() -> dict:
    """Read-only Windows readiness report without exposing tokens or keys."""
    return call("studio_status")


@mcp.tool()
def list_projects(limit: int = 20) -> list[dict]:
    """List recent local projects and publishing states."""
    return call("list_projects", limit=limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
