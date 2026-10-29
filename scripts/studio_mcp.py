"""VideoNews AI Studio: local-first, review-gated orchestration of the existing engine.

No third-party API calls occur at import time. Never run this server on an
unauthenticated public network endpoint: it has filesystem and publishing powers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
import copy
import contextlib
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()
_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="videonews-studio")
_ID = re.compile(r"^[0-9a-f]{32}$")
_SUPPORTED = {"short": "9:16", "long": "16:9"}


class StudioError(RuntimeError):
    pass


class VideoNewsStudio:
    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or os.getenv("VIDEO_STUDIO_DIR", "output/studio")).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "_imports").mkdir(parents=True, exist_ok=True)
        jobs_dir = self.workspace / "jobs"
        if jobs_dir.is_dir():
            for path in jobs_dir.glob("[0-9a-f]" * 32 + ".json"):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                    if record.get("status") in ("queued", "running"):
                        record["status"] = "interrupted"
                        record["error"] = "Studio process exited before the job completed; review artifacts before retrying."
                        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                except (OSError, json.JSONDecodeError):
                    continue

    def _dir(self, job_id: str) -> Path:
        if not _ID.fullmatch(job_id):
            raise ValueError("Invalid job identifier")
        return self.workspace / job_id

    def _read(self, job_id: str) -> dict[str, Any]:
        path = self._dir(job_id) / "project.json"
        if not path.is_file():
            raise StudioError("Project not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, project: dict[str, Any]) -> None:
        folder = self._dir(project["id"])
        folder.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".project-", suffix=".json", dir=folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(project, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, folder / "project.json")
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _jobs_dir(self) -> Path:
        folder = self.workspace / "jobs"
        folder.mkdir(exist_ok=True)
        return folder

    def start_job(self, action: str, project_id: str, arguments: dict[str, Any] | None = None,
                  idempotency_key: str = "") -> dict:
        actions = {"generate_images", "generate_stock_images", "create_thumbnail", "generate_voice",
                   "generate_subtitles", "render_preview", "render_video"}
        if action not in actions:
            raise ValueError("Unsupported asynchronous studio action")
        if idempotency_key and not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", idempotency_key):
            raise ValueError("idempotency_key must contain 8-100 safe characters")
        self._read(project_id)
        folder = self._jobs_dir()
        if idempotency_key:
            idem = folder / (hashlib.sha256(idempotency_key.encode()).hexdigest() + ".json")
            with _LOCK:
                if idem.is_file():
                    existing_id = json.loads(idem.read_text(encoding="utf-8"))["job_id"]
                    existing = self.get_job(existing_id)
                    if existing.get("action") != action or existing.get("project_id") != project_id:
                        raise StudioError("Idempotency key was already used for a different job")
                    return existing
        job_id = uuid.uuid4().hex
        record = {"job_id": job_id, "project_id": project_id, "action": action,
                  "status": "queued", "created_at": datetime.now(timezone.utc).isoformat(),
                  "result": None, "error": None}
        path = folder / (job_id + ".json")
        with _LOCK:
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            if idempotency_key:
                idem.write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
        _JOB_EXECUTOR.submit(self._run_job, path, record, dict(arguments or {}))
        return {"job_id": job_id, "project_id": project_id, "status": "queued"}

    def _run_job(self, path: Path, record: dict[str, Any], arguments: dict[str, Any]) -> None:
        record["status"] = "running"
        record["started_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            # Provider libraries print progress; keep it off the stdio MCP protocol channel.
            with contextlib.redirect_stdout(sys.stderr):
                result = getattr(self, record["action"])(record["project_id"], **arguments)
            record["status"] = "succeeded"
            record["result"] = result
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = f"{type(exc).__name__}: {exc}"[:1000]
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_job(self, job_id: str) -> dict:
        if not _ID.fullmatch(job_id):
            raise ValueError("Invalid job identifier")
        path = self._jobs_dir() / (job_id + ".json")
        if not path.is_file():
            raise StudioError("Job not found")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _config() -> dict[str, Any]:
        from scripts.runtime_config import load_runtime_config
        return load_runtime_config()

    @staticmethod
    def _chatbot(config: dict[str, Any]):
        from scripts.AI.natural_language_generation import Chatbot
        return Chatbot(
            language=config["article_settings"]["language"],
            model=config["article_settings"]["model"],
            providers=config["llm"]["providers"],
        )

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _invalidate_review(self, project: dict[str, Any]) -> None:
        project.pop("approval_digest", None)
        project.pop("review_fingerprint", None)
        project.pop("owner_authorization", None)
        project["status"] = "draft"

    @staticmethod
    def _revision(project: dict[str, Any], section: str, value: Any) -> None:
        """Keep an auditable, bounded history of ChatGPT-authored changes."""
        versions = project.setdefault("versions", [])
        versions.append({
            "version": len(versions) + 1,
            "section": section,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "value": copy.deepcopy(value),
        })
        del versions[:-50]
        project["schema_version"] = 2

    def create_project(self, title: str, video_format: str = "short") -> dict:
        title = title.strip() if isinstance(title, str) else ""
        if not 5 <= len(title) <= 240:
            raise ValueError("title must contain 5-240 characters")
        if video_format not in _SUPPORTED:
            raise ValueError("video_format must be short or long")
        project = {
            "schema_version": 2, "id": uuid.uuid4().hex, "title": title,
            "format": video_format, "aspect_ratio": _SUPPORTED[video_format],
            "sources": [], "editorial_brief": {}, "script": "", "narration": [],
            "storyboard": [], "youtube_metadata": {}, "asset_records": [],
            "source_text": "", "source_url": "", "summary": "", "images": [],
            "voice": "", "word_boundaries": "", "subtitles": "", "video": "", "status": "draft",
            "video_id": "", "privacy": "private", "versions": [],
        }
        with _LOCK:
            self._revision(project, "project", {"title": title, "format": video_format})
            self._save(project)
        return self._public(project)

    def save_sources(self, job_id: str, sources: list[dict[str, Any]]) -> dict:
        if not isinstance(sources, list) or not 1 <= len(sources) <= 30:
            raise ValueError("sources must contain 1-30 source records")
        from scripts.url_safety import validate_public_url
        clean = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("each source must be an object")
            url = str(source.get("url", "")).strip()
            validate_public_url(url)
            clean.append({
                "title": str(source.get("title", ""))[:500], "url": url,
                "publisher": str(source.get("publisher", source.get("source", "")))[:200],
                "published_at": str(source.get("published_at", source.get("publishedAt", "")))[:100],
                "summary": str(source.get("summary", source.get("description", "")))[:5000],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            })
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            project["sources"] = clean
            project["source_url"] = clean[0]["url"]
            project["source_text"] = clean[0]["summary"]
            self._revision(project, "sources", clean)
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    def save_editorial_brief(self, job_id: str, brief: dict[str, Any]) -> dict:
        if not isinstance(brief, dict) or len(json.dumps(brief, ensure_ascii=False)) > 20000:
            raise ValueError("brief must be an object no larger than 20000 characters")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            project["editorial_brief"] = copy.deepcopy(brief)
            self._revision(project, "editorial_brief", brief)
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    def save_script(self, job_id: str, narration: str | list[dict[str, Any]]) -> dict:
        if isinstance(narration, str):
            text = narration.strip()
            segments = [{"text": text, "scene_id": "scene-1"}] if text else []
        elif isinstance(narration, list):
            if not 1 <= len(narration) <= 200:
                raise ValueError("narration must contain 1-200 segments")
            segments = []
            for index, segment in enumerate(narration, 1):
                if not isinstance(segment, dict) or not isinstance(segment.get("text"), str):
                    raise ValueError("each narration segment must include text")
                text_part = segment["text"].strip()
                if not text_part or len(text_part) > 4000:
                    raise ValueError("narration segment text must contain 1-4000 characters")
                segments.append({"text": text_part, "scene_id": str(segment.get("scene_id", f"scene-{index}"))[:100]})
            text = " ".join(item["text"] for item in segments)
        else:
            raise ValueError("narration must be text or a list of segments")
        if not 30 <= len(text) <= 20000:
            raise ValueError("script must contain 30-20000 characters")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            changed = project.get("script") != text
            project["script"] = text
            project["narration"] = segments
            project["summary"] = ""
            self._revision(project, "script", {"narration": segments})
            if changed:
                project["images"] = []
                project["asset_records"] = []
                project["voice"] = project["word_boundaries"] = ""
                project["subtitles"] = project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    def save_storyboard(self, job_id: str, scenes: list[dict[str, Any]]) -> dict:
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 60:
            raise ValueError("storyboard must contain 1-60 scenes")
        normalized = []
        scene_ids = set()
        for index, scene in enumerate(scenes, 1):
            if not isinstance(scene, dict):
                raise ValueError("each scene must be an object")
            scene_id = str(scene.get("id", f"scene-{index}"))[:100]
            if not scene_id or scene_id in scene_ids:
                raise ValueError("scene IDs must be non-empty and unique")
            scene_ids.add(scene_id)
            visual_prompt = str(scene.get("visual_prompt", ""))[:2000]
            normalized.append({
                "id": scene_id,
                "narration": str(scene.get("narration", ""))[:4000],
                "visual_prompt": visual_prompt,
                "on_screen_text": str(scene.get("on_screen_text", ""))[:500],
                "visual_type": str(scene.get("visual_type", "illustration"))[:40],
                "duration_seconds": scene.get("duration_seconds"),
                "asset_ids": list(scene.get("asset_ids", []))[:20],
            })
            duration = normalized[-1]["duration_seconds"]
            if duration is not None and (not isinstance(duration, (int, float)) or not 0.2 <= duration <= 120):
                raise ValueError("scene duration must be between 0.2 and 120 seconds")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            previous = {scene["id"]: scene for scene in project.get("storyboard", [])}
            unchanged_scene_ids = {
                scene["id"] for scene in normalized
                if scene["id"] in previous
                and scene["visual_prompt"] == previous[scene["id"]].get("visual_prompt", "")
                and scene["visual_type"] == previous[scene["id"]].get("visual_type", "illustration")
            }
            retained_assets = [
                asset for asset in project.get("asset_records", [])
                if asset.get("scene_id") in unchanged_scene_ids
            ]
            retained_by_scene: dict[str, list[str]] = {}
            for asset in retained_assets:
                retained_by_scene.setdefault(asset["scene_id"], []).append(asset["id"])
            for scene in normalized:
                scene["asset_ids"] = retained_by_scene.get(scene["id"], [])
            project["storyboard"] = normalized
            project["asset_records"] = retained_assets
            project["images"] = [asset["path"] for asset in retained_assets]
            project["video"] = ""
            self._revision(project, "storyboard", normalized)
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    def save_youtube_metadata(self, job_id: str, metadata: dict[str, Any]) -> dict:
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        title = str(metadata.get("title", "")).strip()
        description = str(metadata.get("description", "")).strip()
        tags = metadata.get("tags", [])
        if not 5 <= len(title) <= 100 or len(description) > 5000 or not isinstance(tags, list):
            raise ValueError("invalid YouTube title, description or tags")
        clean = {"title": title, "description": description,
                 "tags": [str(tag)[:60] for tag in tags[:30]],
                 "hashtags": [str(tag)[:80] for tag in metadata.get("hashtags", [])[:15]],
                 "thumbnail_concept": str(metadata.get("thumbnail_concept", ""))[:1000],
                 "thumbnail_text": str(metadata.get("thumbnail_text", title))[:100],
                 "thumbnail_path": "",
                 "language": str(metadata.get("language", "es"))[:10],
                 "category_id": str(metadata.get("category_id", "25"))[:4],
                 "contains_synthetic_media": bool(metadata.get("contains_synthetic_media", False))}
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            if any(item.get("synthetic_media") for item in project.get("asset_records", [])):
                clean["contains_synthetic_media"] = True
            project["youtube_metadata"] = clean
            project["title"] = title
            project["summary"] = description
            self._revision(project, "youtube_metadata", clean)
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    def research_news(self, query: str, language: str = "es", limit: int = 10,
                      country: str = "es", category: str = "") -> dict:
        """Read-only search. Results are source leads, not verified claims."""
        if not query.strip() or len(query) > 200:
            raise ValueError("query must contain 1-200 characters")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be 1-20")
        config = self._config()
        api_key = config["serpapi"]["api_key"]
        if not api_key:
            raise StudioError("SERPAPI_API_KEY is required for news research")
        from scripts.url_safety import validate_public_url
        from scripts.DataFetcher.serpapi_client import SerpAPIProvider
        provider = SerpAPIProvider(api_key=api_key, use_cache=config["serpapi"]["use_cache"],
                                   cache_ttl_hours=config["serpapi"]["cache_ttl_hours"])
        if not re.fullmatch(r"[a-zA-Z]{2}", country):
            raise ValueError("country must be a two-letter country code")
        if category and category not in ("business", "entertainment", "general", "health", "science", "sports", "technology"):
            raise ValueError("Unsupported news category")
        from difflib import SequenceMatcher
        from scripts.dbControllers.processed_news_controller import is_url_processed
        raw = provider.search_news(query, language=language, country=country,
                                   category=category or None, limit=limit)
        articles = []
        for item in raw:
            title = str(item.get("title", ""))
            duplicate_of = next((entry["url"] for entry in articles
                                 if SequenceMatcher(None, title.lower(), entry["title"].lower()).ratio() >= 0.82), None)
            url = str(item.get("url", ""))
            try:
                validate_public_url(url)
                url_validated = True
            except ValueError:
                url_validated = False
            source = item.get("source", "")
            source_name = (source.get("name", source.get("title", ""))
                           if isinstance(source, dict) else str(source))
            published_at = item.get("publishedAt")
            published_at_iso = None
            if published_at:
                try:
                    from dateutil import parser as dateparser
                    parsed_date = dateparser.parse(str(published_at).replace(" UTC", ""))
                    published_at_iso = parsed_date.isoformat()
                except (ValueError, TypeError, OverflowError):
                    pass
            try:
                already_processed = bool(url and is_url_processed(url))
            except Exception:
                already_processed = False
            articles.append({
                "title": title, "url": url, "url_validated": url_validated,
                "description": item.get("description", ""), "source": source_name,
                "publishedAt": published_at, "published_at_iso": published_at_iso,
                "already_processed": already_processed, "duplicate_of": duplicate_of,
            })
        return {"query": query, "country": country.lower(), "language": language,
                "count": len(articles), "articles": articles,
                "scoring_rubric": "ChatGPT should judge timeliness, source quality, audience relevance and visual potential qualitatively; no search-volume or virality analytics are supplied.",
                "editorial_note": "These are leads. Verify original sources, dates and claims before publication."}

    def retrieve_article(self, url: str) -> dict:
        from scripts.DataFetcher.news_extractor import NewsExtractor
        from scripts.url_safety import validate_public_url
        validate_public_url(url)
        article = NewsExtractor().extract_article(url)
        if not article or not article.text:
            raise StudioError("Could not extract article text from the supplied source")
        return {"title": article.title[:500], "url": url,
                "authors": article.authors[:20], "published_at": str(article.publish_date or ""),
                "text": article.text[:12000], "truncated": len(article.text) > 12000}

    def create_script(self, title: str, source_text: str, source_url: str = "",
                      video_format: str = "short") -> dict:
        """Compatibility helper that persists caller-authored text without invoking an LLM."""
        if video_format not in _SUPPORTED:
            raise ValueError("video_format must be short or long")
        title = title.strip()
        source_text = source_text.strip()
        if not 5 <= len(title) <= 240 or not 30 <= len(source_text) <= 12000:
            raise ValueError("title (5-240) and source_text (30-12000) required")
        project = self.create_project(title, video_format)
        if source_url:
            self.save_sources(project["id"], [{"url": source_url, "title": title, "summary": source_text}])
        return self.save_script(project["id"], source_text)

    @staticmethod
    def _public(project: dict) -> dict:
        return {key: value for key, value in project.items()
                if key not in ("approval_digest", "review_fingerprint")}

    def get_project(self, job_id: str) -> dict:
        with _LOCK:
            return self._public(self._read(job_id))

    def list_assets(self, job_id: str) -> list[dict[str, Any]]:
        with _LOCK:
            return copy.deepcopy(self._read(job_id).get("asset_records", []))

    def revise_script(self, job_id: str, script: str) -> dict:
        if len(script.strip()) < 30 or len(script) > 20000:
            raise ValueError("script must be 30-20000 characters")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            project["script"] = script.strip()
            for key, value in (("images", []), ("voice", ""), ("word_boundaries", ""),
                               ("subtitles", ""), ("video", "")):
                project[key] = value
            self._invalidate_review(project)
            self._save(project)
            return self._public(project)

    @staticmethod
    def _require_editable(project: dict) -> None:
        if project["status"] in ("uploading", "upload_unknown", "published"):
            raise StudioError("Publication underway or completed; create a new project")

    def generate_images(self, job_id: str, prompts: list[str] | None = None,
                        count: int = 5, style: str = "PHOTOREALISTIC") -> dict:
        if not 1 <= count <= 12:
            raise ValueError("count must be 1-12")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            if prompts is None:
                prompts = [scene["visual_prompt"] for scene in project.get("storyboard", [])
                           if scene.get("visual_prompt")]
            if not prompts:
                raise StudioError("Save a ChatGPT-authored storyboard or import reviewed assets first")
            if os.getenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "false").lower() not in ("1", "true", "yes"):
                raise StudioError("Paid image generation is disabled; import reviewed assets instead")
            config = self._config()
            from scripts.AI.text_to_image import FluxImageGenerator, StylePreset, AspectRatio
            if style not in StylePreset.__members__:
                raise ValueError("Invalid image style: " + style)
            prompt_list = prompts if prompts is not None else self._chatbot(config).generate_image_descriptions(
                project["script"], count=count)
            if not isinstance(prompt_list, list) or not prompt_list or len(prompt_list) > 12:
                raise StudioError("Expected 1-12 image prompts")
            if any(not isinstance(p, str) or not 5 <= len(p.strip()) <= 1500 for p in prompt_list):
                raise ValueError("Every image prompt must be 5-1500 characters")
            folder = self._dir(job_id)
            (folder / "images").mkdir(exist_ok=True)
            azure = config["azure_images"]
            generator = FluxImageGenerator(
                output_dir=str(folder / "images"),
                azure_endpoint=azure.get("endpoint"), azure_api_key=azure.get("api_key"),
                azure_model=azure.get("model", "MAI-Image-2e"),
            )
            ratio = AspectRatio.SHORTS if project["format"] == "short" else AspectRatio.LANDSCAPE
            output = []
            for prompt in prompt_list:
                generated = Path(generator.generate_image(prompt, StylePreset[style], ratio)).resolve()
                if not generated.is_file() or generated.stat().st_size == 0:
                    raise StudioError("Image generation returned an invalid file")
                # Copy to stable per-project paths, regardless of generator temp location.
                target = folder / "images" / (uuid.uuid4().hex + generated.suffix.lower())
                if generated != target:
                    shutil.copy2(generated, target)
                output.append(str(target))
            project["images"] = output
            project["asset_records"] = [
                {"id": Path(path).stem, "path": path, "sha256": self._hash(Path(path)),
                 "provenance": "generated", "synthetic_media": True, "prompt": prompt}
                for path, prompt in zip(output, prompt_list)
            ]
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "images": output, "prompts": prompt_list}

    def generate_stock_images(self, job_id: str) -> dict:
        """Retrieve one licensed, scene-matched Pexels image per missing scene."""
        from io import BytesIO
        from urllib.parse import urlsplit
        import requests
        from PIL import Image

        config = self._config()
        api_key = config.get("pexels", {}).get("api_key", "")
        if not api_key:
            raise StudioError("PEXELS_API_KEY is required for automatic licensed visuals")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            scenes = project.get("storyboard", [])
            if not scenes:
                raise StudioError("Save a scene-by-scene storyboard before requesting stock images")
            existing = {record.get("scene_id") for record in project.get("asset_records", [])}
            folder = self._dir(job_id) / "images"
            folder.mkdir(exist_ok=True)
            records = project.setdefault("asset_records", [])
            for scene in scenes:
                scene_id = scene.get("id")
                prompt = str(scene.get("visual_prompt", "")).strip()
                if scene_id in existing:
                    continue
                if not prompt:
                    raise StudioError(f"Scene {scene_id} has no visual_prompt")
                search = requests.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": prompt[:500], "per_page": 1,
                            "orientation": "portrait" if project["format"] == "short" else "landscape"},
                    headers={"Authorization": api_key}, timeout=(10, 30),
                )
                search.raise_for_status()
                photos = search.json().get("photos", [])
                if not photos:
                    raise StudioError(f"Pexels returned no licensed image for scene {scene_id}")
                photo = photos[0]
                image_url = str(photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large", ""))
                parsed = urlsplit(image_url)
                if parsed.scheme != "https" or parsed.hostname != "images.pexels.com":
                    raise StudioError("Pexels returned an untrusted image host")
                from scripts.url_safety import validate_public_url
                validate_public_url(image_url)
                response = requests.get(image_url, stream=True, allow_redirects=False,
                                        timeout=(10, 45))
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
                if content_type not in ("image/jpeg", "image/png", "image/webp"):
                    raise StudioError("Pexels returned an unsupported image type")
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > 20 * 1024 * 1024:
                        raise StudioError("Pexels image exceeds the 20MB import limit")
                if not content:
                    raise StudioError("Pexels returned an empty image")
                try:
                    with Image.open(BytesIO(content)) as image:
                        image.verify()
                        image_format = image.format
                except Exception as exc:
                    raise StudioError("Pexels response was not a valid image") from exc
                extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image_format)
                if not extension:
                    raise StudioError("Pexels image format is not supported")
                target = folder / (uuid.uuid4().hex + extension)
                target.write_bytes(content)
                credit = {"provider": "Pexels", "license": "Pexels License",
                          "source_url": str(photo.get("url", "")),
                          "photographer": str(photo.get("photographer", "")),
                          "photographer_url": str(photo.get("photographer_url", "")),
                          "visual_prompt": prompt}
                records.append({"id": target.stem, "scene_id": scene_id, "path": str(target),
                                "sha256": self._hash(target), "mime_type": content_type,
                                "synthetic_media": False, "provenance": credit,
                                "imported_at": datetime.now(timezone.utc).isoformat()})
                existing.add(scene_id)
                scene.setdefault("asset_ids", []).append(target.stem)
                project["images"] = [item["path"] for scene_item in scenes
                                      for item in records if item.get("scene_id") == scene_item.get("id")]
                project["video"] = ""
                self._invalidate_review(project)
                self._save(project)
            return {"job_id": job_id, "assets": [r for r in records if r.get("scene_id") in existing],
                    "provider": "Pexels", "license": "Pexels License"}

    def create_thumbnail(self, job_id: str) -> dict:
        """Compose a readable 16:9 thumbnail from a project asset and ChatGPT text."""
        from PIL import Image, ImageDraw, ImageFont, ImageOps
        import textwrap

        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            images = project.get("images", [])
            if not images or not Path(images[0]).is_file():
                raise StudioError("Create or import at least one scene visual before the thumbnail")
            metadata = project.get("youtube_metadata", {})
            title = str(metadata.get("thumbnail_text") or metadata.get("title", project["title"]))
            text_lines = textwrap.wrap(title[:80], width=22, break_long_words=True)[:3]
            source = Image.open(images[0]).convert("RGB")
            canvas = ImageOps.fit(source, (1280, 720), method=Image.Resampling.LANCZOS).convert("RGBA")
            overlay = Image.new("RGBA", canvas.size, (5, 20, 34, 95))
            canvas = Image.alpha_composite(canvas, overlay)
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((0, 0, 18, 720), fill=(0, 190, 210, 255))
            draw.rectangle((56, 492, 1215, 704), fill=(4, 18, 31, 208))
            font_path = Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf"
            font_size = 72
            brand_font = ImageFont.truetype(str(font_path), 25) if font_path.is_file() else ImageFont.load_default()
            while font_size > 34:
                font = ImageFont.truetype(str(font_path), font_size) if font_path.is_file() else ImageFont.load_default()
                boxes = [draw.textbbox((0, 0), line, font=font) for line in text_lines]
                total_height = sum(box[3] - box[1] for box in boxes) + 3 * (len(boxes) - 1)
                if all(box[2] <= 1110 for box in boxes) and total_height <= 130:
                    break
                font_size -= 4
            draw.text((82, 505), "NEWSPHERE", font=brand_font, fill=(0, 215, 225, 255))
            text_y = 545
            for index, line in enumerate(text_lines):
                box = draw.textbbox((0, 0), line, font=font)
                draw.text((82, text_y), line, font=font,
                          fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
                text_y += box[3] - box[1] + 3
            output = self._dir(job_id) / "thumbnail.jpg"
            canvas.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
            metadata["thumbnail_path"] = str(output)
            project["youtube_metadata"] = metadata
            self._save(project)
            with Image.open(output) as check:
                if check.size != (1280, 720) or check.format != "JPEG":
                    raise StudioError("Generated thumbnail failed format validation")
            return {"job_id": job_id, "thumbnail": str(output), "width": 1280,
                    "height": 720, "bytes": output.stat().st_size, "text": title}

    def import_asset(self, job_id: str, staged_filename: str, scene_id: str,
                     provenance: dict[str, Any]) -> dict:
        """Import an image only from the explicitly staged, workspace-scoped inbox."""
        if not isinstance(staged_filename, str) or Path(staged_filename).name != staged_filename:
            raise ValueError("staged_filename must be a plain filename in the studio import inbox")
        if (not isinstance(provenance, dict) or not str(provenance.get("source", "")).strip()
                or not isinstance(provenance.get("synthetic_media"), bool)):
            raise ValueError("provenance.source and boolean provenance.synthetic_media are required")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            inbox = (self.workspace / "_imports").resolve()
            source = (inbox / staged_filename).resolve()
            if source.parent != inbox or not source.is_file() or source.stat().st_size > 40 * 1024 * 1024:
                raise StudioError("Asset must be a file <=40MB in the configured studio import inbox")
            from PIL import Image
            try:
                with Image.open(source) as image:
                    image.verify()
                    image_format = image.format
                    mime = Image.MIME.get(image_format)
                    extension = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}.get(image_format, "")
            except Exception as exc:
                raise StudioError("Imported asset is not a valid supported image") from exc
            if mime not in ("image/jpeg", "image/png", "image/webp") or not extension:
                raise StudioError("Only JPEG, PNG, and WebP assets are supported")
            target_dir = self._dir(job_id) / "images"
            target_dir.mkdir(exist_ok=True)
            target = target_dir / (uuid.uuid4().hex + extension)
            shutil.copy2(source, target)
            record = {
                "id": target.stem, "scene_id": str(scene_id)[:100], "path": str(target),
                "sha256": self._hash(target), "mime_type": mime,
                "synthetic_media": provenance["synthetic_media"],
                "provenance": {key: str(value)[:1000] for key, value in provenance.items()},
                "imported_at": datetime.now(timezone.utc).isoformat(),
            }
            scene_ids = {scene.get("id") for scene in project.get("storyboard", [])}
            if scene_ids and record["scene_id"] not in scene_ids:
                target.unlink(missing_ok=True)
                raise ValueError("scene_id must reference a scene in the saved storyboard")
            project.setdefault("asset_records", []).append(record)
            scene_order = {scene["id"]: index
                           for index, scene in enumerate(project.get("storyboard", []))}
            project["asset_records"].sort(key=lambda asset: (
                scene_order.get(asset.get("scene_id", ""), len(scene_order)),
                asset.get("imported_at", ""),
            ))
            for scene in project.get("storyboard", []):
                if scene.get("id") == record["scene_id"]:
                    scene.setdefault("asset_ids", []).append(record["id"])
            project["images"] = [item["path"] for item in project["asset_records"]]
            project["video"] = ""
            self._revision(project, "asset_import", record)
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "asset": record}

    def generate_voice(self, job_id: str, voice: str = "es-ES-ElviraNeural") -> dict:
        """Use the existing Edge TTS engine and its word-level timing events."""
        if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+Neural", voice):
            raise ValueError("Invalid Edge TTS voice name")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            from scripts.AI.text_to_speech import TTSEdge
            folder = self._dir(job_id)
            audio = folder / "narration.mp3"
            boundaries = folder / "word_boundaries.srt"
            engine = TTSEdge(output_dir=str(folder))
            engine.text_to_speech_file(
                project["script"], language=voice[:2], voice=voice,
                output_path=str(audio), srt_path=str(boundaries),
            )
            if (not audio.is_file() or audio.stat().st_size == 0
                    or not boundaries.is_file() or not boundaries.stat().st_size):
                raise StudioError("TTS did not produce audio with word-boundary subtitles")
            project["voice"] = str(audio)
            project["word_boundaries"] = str(boundaries)
            project["subtitles"] = ""
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "voice": str(audio), "word_boundaries": str(boundaries)}

    def generate_subtitles(self, job_id: str, max_words: int = 5) -> dict:
        if not 1 <= max_words <= 12:
            raise ValueError("max_words must be 1-12")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            boundary_path = Path(project["word_boundaries"]) if project.get("word_boundaries") else None
            if (not boundary_path or not boundary_path.is_file()
                    or not boundary_path.read_text(encoding="utf-8").strip()):
                raise StudioError("Generate Edge TTS narration with word boundaries first")
            from scripts.MediaManagers.SRT_Processor import SRTProcessor
            path = self._dir(job_id) / "subtitles.srt"
            shutil.copy2(boundary_path, path)
            processor = SRTProcessor(str(path), max_words=max_words,
                                     max_duration=2.0 if project["format"] == "short" else 4.0)
            processor.process()
            if not path.stat().st_size:
                raise StudioError("Subtitle processing produced an empty SRT")
            project["subtitles"] = str(path)
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "subtitles": str(path), "bytes": path.stat().st_size}

    @staticmethod
    def _probe_duration(path: Path) -> float:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            raise StudioError("ffprobe could not read the narration duration")
        try:
            duration = float(result.stdout.strip())
        except ValueError as exc:
            raise StudioError("ffprobe returned an invalid narration duration") from exc
        if duration <= 0:
            raise StudioError("Narration duration must be positive")
        return duration

    @staticmethod
    def _scene_image_durations(project: dict, audio_duration: float) -> list[float] | None:
        """Match storyboard narration segments to actual TTS word boundaries."""
        scenes = project.get("storyboard", [])
        records = project.get("asset_records", [])
        raw_path = Path(project.get("word_boundaries", "")) if project.get("word_boundaries") else None
        if not scenes or not records or not raw_path or not raw_path.is_file():
            return None
        segment_text = {item.get("scene_id"): item.get("text", "")
                        for item in project.get("narration", [])}
        scene_texts = [scene.get("narration") or segment_text.get(scene.get("id"), "")
                       for scene in scenes]
        if not any(scene_texts):
            return None

        from scripts.MediaManagers.SRT_Processor import SRTProcessor
        entries = SRTProcessor(str(raw_path)).parse_srt()
        words = [re.findall(r"[^\W_]+", entry["text"].casefold(), flags=re.UNICODE)
                 for entry in entries]
        tokens = [parts[0] if parts else "" for parts in words]
        starts = []
        cursor = 0
        for scene_text in scene_texts:
            expected = re.findall(r"[^\W_]+", scene_text.casefold(), flags=re.UNICODE)
            if not expected:
                raise StudioError("Every storyboard scene needs narration matching the saved script")
            found = next((index for index in range(cursor, len(tokens) - len(expected) + 1)
                          if tokens[index:index + len(expected)] == expected), None)
            if found is None:
                raise StudioError("Storyboard narration does not match TTS word boundaries; align it to the saved script")
            starts.append(entries[found]["start"])
            cursor = found + len(expected)

        boundaries = []
        for index, start in enumerate(starts):
            next_start = starts[index + 1] if index + 1 < len(starts) else audio_duration
            boundaries.append(max(0.05, next_start - (0.0 if index == 0 else start)))

        records_by_scene: dict[str, list[dict]] = {}
        for record in records:
            records_by_scene.setdefault(record.get("scene_id", ""), []).append(record)
        duration_by_path = {}
        for scene, duration in zip(scenes, boundaries):
            scene_records = records_by_scene.get(scene.get("id"), [])
            if not scene_records:
                raise StudioError(f"Storyboard scene {scene.get('id')} has no imported image asset")
            for record in scene_records:
                duration_by_path[record["path"]] = duration / len(scene_records)
        image_paths = project.get("images", [])
        if (len(duration_by_path) != len(image_paths)
                or any(path not in duration_by_path for path in image_paths)):
            raise StudioError("Scene assets and project image order do not match")
        return [duration_by_path[path] for path in image_paths]

    def render_video(self, job_id: str) -> dict:
        """Call existing FFmpeg VideoAssembler; no publishing side effects."""
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            images = [Path(s) for s in project["images"]]
            if not images or not all(p.is_file() and p.stat().st_size for p in images):
                raise StudioError("Generate images first")
            audio = Path(project["voice"]) if project["voice"] else None
            srt = Path(project["subtitles"]) if project["subtitles"] else None
            if not audio or not audio.is_file() or not srt or not srt.is_file() or not srt.stat().st_size:
                raise StudioError("Generate narration and subtitles first")
            from scripts.video_assembler import VideoAssembler
            from scripts.helpers.media_helper import Position
            output = self._dir(job_id) / "video.mp4"
            duration = self._probe_duration(audio)
            image_durations = self._scene_image_durations(project, duration)
            assembler = VideoAssembler(subtitle_file=str(srt), voiceover_file=str(audio),
                                       output_file=str(output), media_images=[str(p) for p in images],
                                       aspect_ratio=_SUPPORTED[project["format"]],
                                       image_durations=image_durations)
            assembler.assemble_video(position=Position.BOTTOM_CENTER)
            if not output.is_file() or not output.stat().st_size:
                raise StudioError("FFmpeg returned no playable video")
            project["video"] = str(output)
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "video": str(output), "bytes": output.stat().st_size}

    def render_preview(self, job_id: str) -> dict:
        """Produce a low-resolution review render without approving publication."""
        with _LOCK:
            old_resolution = os.getenv("VIDEO_RENDER_RESOLUTION")
            os.environ["VIDEO_RENDER_RESOLUTION"] = "360p"
            try:
                project = self._read(job_id)
                self._require_editable(project)
                images = [Path(s) for s in project["images"]]
                audio = Path(project["voice"]) if project["voice"] else None
                srt = Path(project["subtitles"]) if project["subtitles"] else None
                if not images or not all(p.is_file() and p.stat().st_size for p in images):
                    raise StudioError("Import reviewed images first")
                if not audio or not audio.is_file() or not srt or not srt.is_file() or not srt.stat().st_size:
                    raise StudioError("Generate narration and subtitles first")
                from scripts.video_assembler import VideoAssembler
                from scripts.helpers.media_helper import Position
                output = self._dir(job_id) / "preview.mp4"
                duration = self._probe_duration(audio)
                image_durations = self._scene_image_durations(project, duration)
                VideoAssembler(subtitle_file=str(srt), voiceover_file=str(audio),
                               output_file=str(output), media_images=[str(p) for p in images],
                               aspect_ratio=_SUPPORTED[project["format"]],
                               image_durations=image_durations).assemble_video(
                                   position=Position.BOTTOM_CENTER)
                if not output.is_file() or not output.stat().st_size:
                    raise StudioError("Preview render produced no playable video")
                project["preview"] = str(output)
                self._save(project)
                return {"job_id": job_id, "preview": str(output), "bytes": output.stat().st_size}
            finally:
                if old_resolution is None:
                    os.environ.pop("VIDEO_RENDER_RESOLUTION", None)
                else:
                    os.environ["VIDEO_RENDER_RESOLUTION"] = old_resolution

    def review_video(self, job_id: str) -> dict:
        """Read-only quality inspection. Owner approval is issued by the local console."""
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            problems = []
            video = Path(project["video"]) if project["video"] else None
            if not video or not video.is_file() or not video.stat().st_size:
                problems.append("Missing rendered video")
            if not project["source_url"]:
                problems.append("No source URL: verify traceable primary sources")
            if not project["script"].strip():
                problems.append("Missing narration script")
            if not project["images"]:
                problems.append("Missing illustrations")
            if not project["subtitles"] or not Path(project["subtitles"]).is_file():
                problems.append("Missing subtitles")
            duration = None
            if video and video.is_file() and video.stat().st_size:
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                                        str(video)], capture_output=True, text=True, timeout=20)
                try:
                    duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0
                except ValueError:
                    duration = 0
                if duration <= 0:
                    problems.append("Invalid video duration")
            result = {"job_id": job_id, "duration_seconds": duration, "issues": problems,
                      "requires_human_fact_check": True, "privacy": "private",
                      "ready_for_editorial_review": not problems}
            return result

    def issue_owner_authorization(self, job_id: str, *, owner_confirmed: bool,
                                  target_account_id: str, privacy_status: str = "private",
                                  ttl_seconds: int = 600) -> dict:
        """Mint a one-use exact-video grant after explicit owner confirmation."""
        if not owner_confirmed:
            raise StudioError("Explicit owner confirmation is required")
        if not re.fullmatch(r"[A-Za-z0-9_-]{5,100}", target_account_id):
            raise ValueError("A YouTube channel ID is required")
        from scripts.publishing_policy import PRIVACY_STATUSES
        if privacy_status not in PRIVACY_STATUSES:
            raise ValueError("privacy_status must be public, private, or unlisted")
        if not 60 <= ttl_seconds <= 900:
            raise ValueError("Authorization lifetime must be 60-900 seconds")
        with _LOCK:
            project = self._read(job_id)
            report = self.review_video(job_id)
            if not report["ready_for_editorial_review"]:
                raise StudioError("Resolve review issues before owner authorization")
            video = Path(project["video"]).resolve()
            metadata = project.get("youtube_metadata", {})
            if not metadata.get("title"):
                raise StudioError("Save complete YouTube metadata before approval")
            authorization = {
                "token": uuid.uuid4().hex,
                "project_id": job_id,
                "video_sha256": self._hash(video),
                "target_account_id": target_account_id,
                "privacy": privacy_status, "operation": "youtube_upload",
                "expires_at": datetime.now(timezone.utc).timestamp() + ttl_seconds,
            }
            (self._dir(job_id) / "owner-authorization.json").write_text(
                json.dumps(authorization), encoding="utf-8")
            project["status"] = "owner_approved"
            self._save(project)
            return {"project_id": job_id, "target_account_id": target_account_id,
                    "privacy": privacy_status, "expires_in_seconds": ttl_seconds,
                    "video_sha256": authorization["video_sha256"]}

    def publish_youtube(self, job_id: str,
                        privacy_status: str | None = None) -> dict:
        """Publish at the owner-enrolled status (PUBLIC by default) after verification."""
        with _LOCK:
            project = self._read(job_id)
            if project["status"] == "published":
                return {"job_id": job_id, "video_id": project["video_id"],
                        "url": "https://www.youtube.com/watch?v=" + project["video_id"],
                        "privacy": project.get("privacy_status", "unknown"),
                        "already_published": True}
            if project["status"] in ("uploading", "upload_unknown",
                                      "upload_verification_failed"):
                raise StudioError("Upload outcome is uncertain; reconcile it before any retry")
            authorization_path = self._dir(job_id) / "owner-authorization.json"
            video = Path(project["video"]).resolve()
            if not video.is_file():
                raise StudioError("Rendered video is missing")
            video_hash = self._hash(video)
            from scripts import publishing_policy
            automatic_policy = None
            if authorization_path.is_file():
                try:
                    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise StudioError("Local owner authorization is missing or invalid") from exc
                if (project["status"] != "owner_approved"
                        or authorization.get("project_id") != job_id
                        or authorization.get("privacy") not in publishing_policy.PRIVACY_STATUSES
                        or privacy_status not in (None, authorization.get("privacy"))
                        or authorization.get("operation") != "youtube_upload"
                        or authorization.get("expires_at", 0) < datetime.now(timezone.utc).timestamp()
                        or not video.is_file()
                        or self._hash(video) != authorization.get("video_sha256")):
                    raise StudioError("Owner authorization expired or no longer matches this upload")
                requested_privacy = authorization["privacy"]
            else:
                automatic_policy = publishing_policy.load()
                if not automatic_policy:
                    raise StudioError("Owner must enroll once in automatic YouTube publishing from the local console")
                requested_privacy = privacy_status or automatic_policy["privacy_status"]
                if requested_privacy not in automatic_policy["allowed_privacy_statuses"]:
                    raise StudioError("Requested privacy status is not allowed by the owner-enrolled policy")
                report = self.review_video(job_id)
                if not report["ready_for_editorial_review"]:
                    raise StudioError("Resolve Studio quality issues before publishing")
                history = publishing_policy.records()
                if any(r.get("project_id") == job_id for r in history):
                    raise StudioError("This project already has a publishing attempt; reconcile it or create a new project")
                today = datetime.now(timezone.utc).date().isoformat()
                daily_projects = {
                    r.get("project_id") for r in history
                    if r.get("channel_id") == automatic_policy["channel_id"]
                    and r.get("outcome") == "upload_started"
                    and str(r.get("at", "")).startswith(today)
                }
                daily_count = len(daily_projects)
                if daily_count >= automatic_policy["max_uploads_per_day"]:
                    raise StudioError("Owner-configured daily YouTube upload limit reached")
                metadata = project.get("youtube_metadata", {})
                if not metadata.get("title"):
                    raise StudioError("Save complete YouTube metadata before publishing")
            config = self._config()
            secret_file = Path(config["youtube"]["credentials_file"]).resolve()
            token_file = Path(config["youtube"].get("token_file", ".secrets/token.json")).resolve()
            if not secret_file.is_file():
                raise StudioError("YouTube OAuth client secrets not configured")
            from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
            uploader = YoutubeMediaUploader(client_secrets_file=str(secret_file),
                                            token_file=str(token_file))
            channel = uploader.get_channel_info()
            account_id = channel["id"]
            if automatic_policy:
                if account_id != automatic_policy["channel_id"]:
                    raise StudioError("Authenticated YouTube channel does not match the owner-enrolled channel")
                if channel["title"].strip().casefold() != "newsphere":
                    raise StudioError("Authenticated YouTube channel is not NewSphere")
                if publishing_policy.load() != automatic_policy:
                    raise StudioError("Owner revoked or changed automatic publishing before upload")
            elif account_id != authorization["target_account_id"]:
                raise StudioError("Authorized YouTube account changed; create a new local approval")

            history = publishing_policy.records()
            if any(r.get("project_id") == job_id and r.get("outcome") in (
                    "upload_started", "upload_unknown", "verification_failed", "uploaded")
                   for r in history):
                raise StudioError("This project already has a publishing attempt; reconcile before retry")

            project["status"] = "uploading"
            project["privacy_status"] = requested_privacy
            if authorization_path.is_file():
                authorization_path.unlink(missing_ok=True)
            self._save(project)
            publishing_policy.audit(job_id, video_hash, account_id,
                                    "upload_started", privacy_status=requested_privacy)
            video_id = None
            try:
                metadata = project.get("youtube_metadata", {})
                response = uploader.upload(
                    str(video), title=metadata.get("title", project["title"])[:90],
                    description=metadata.get("description", project["summary"])[:4000],
                    tags=metadata.get("tags", []), privacy_status=requested_privacy,
                    contains_synthetic_media=metadata.get("contains_synthetic_media", False),
                    default_language=metadata.get("language", "es"),
                    thumbnail_path=metadata.get("thumbnail_path") or None,
                )
                video_id = response.get("id")
                if not video_id:
                    raise StudioError("YouTube response lacked a video ID")
                verification = uploader.verify_video(
                    str(video_id), account_id, requested_privacy)
            except BaseException as exc:
                known_id = video_id or getattr(exc, "video_id", None)
                project["status"] = ("upload_verification_failed" if known_id
                                      else "upload_unknown")
                if known_id:
                    project["video_id"] = str(known_id)
                self._save(project)
                publishing_policy.audit(
                    job_id, video_hash, account_id,
                    "verification_failed" if known_id else "upload_unknown",
                    str(known_id or ""), requested_privacy)
                raise
            project["video_id"] = str(video_id)
            project["privacy_status"] = verification["privacy_status"]
            project["youtube_verified_channel_id"] = verification["channel_id"]
            project["status"] = "published"
            self._save(project)
            publishing_policy.audit(job_id, video_hash, account_id, "uploaded",
                                    str(video_id), verification["privacy_status"])
            return {"job_id": job_id, "video_id": video_id,
                    "url": "https://www.youtube.com/watch?v=" + str(video_id),
                    "privacy": verification["privacy_status"],
                    "channel_id": verification["channel_id"],
                    "youtube_verified": True}

    def studio_status(self) -> dict[str, Any]:
        """Read-only runtime checks. Credential presence does not prove an API works."""
        import importlib.metadata
        import shutil
        import sys

        config = self._config()
        try:
            edge_version = importlib.metadata.version("edge-tts")
        except importlib.metadata.PackageNotFoundError:
            edge_version = "not-installed"
        images = config.get("azure_images", {})
        paid_images = os.getenv("VIDEO_ENABLE_PAID_IMAGE_GENERATION", "false").lower() in ("true", "1", "yes")
        from scripts.publishing_policy import load as load_publish_policy
        publishing = load_publish_policy()
        return {
            "server": "VideoNews AI Studio",
            "transport": "stdio",
            "python_311": sys.version_info[:2] == (3, 11),
            "ffmpeg_available": shutil.which("ffmpeg") is not None,
            "ffprobe_available": shutil.which("ffprobe") is not None,
            "news_search_configured": bool(config.get("serpapi", {}).get("api_key")),
            "edge_tts_version": edge_version,
            "image_import_inbox_ready": (self.workspace / "_imports").is_dir(),
            "paid_image_generation_enabled": bool(
                paid_images and images.get("endpoint") and images.get("api_key")
            ),
            "youtube_client_secrets_present": Path(
                config.get("youtube", {}).get("credentials_file", "")
            ).is_file(),
            "youtube_authorization_verified": False,
            "publishing_policy": "automatic_enabled" if publishing
            else "owner_enrollment_required",
            "publishing_default_privacy": publishing["privacy_status"] if publishing else None,
            "publishing_allowed_privacy": (publishing["allowed_privacy_statuses"]
                                           if publishing else []),
        }

    def list_projects(self, limit: int = 20) -> list[dict]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1-100")
        with _LOCK:
            projects = []
            for folder in sorted(self.workspace.iterdir(), key=lambda p: p.stat().st_mtime,
                                 reverse=True):
                if folder.is_dir() and _ID.fullmatch(folder.name) and (folder / "project.json").is_file():
                    data = self._read(folder.name)
                    projects.append({k: data[k] for k in ("id", "title", "status", "format", "video_id")})
                    if len(projects) >= limit:
                        break
            return projects
