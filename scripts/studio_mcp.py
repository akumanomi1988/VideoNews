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
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()
_ID = re.compile(r"^[0-9a-f]{32}$")
_SUPPORTED = {"short": "9:16", "long": "16:9"}


class StudioError(RuntimeError):
    pass


class VideoNewsStudio:
    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace or os.getenv("VIDEO_STUDIO_DIR", "output/studio")).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

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
        project["status"] = "draft"

    def research_news(self, query: str, language: str = "es", limit: int = 10) -> dict:
        """Read-only search. Results are source leads, not verified claims."""
        if not query.strip() or len(query) > 200:
            raise ValueError("query must contain 1-200 characters")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be 1-20")
        config = self._config()
        api_key = config["serpapi"]["api_key"]
        if not api_key:
            raise StudioError("SERPAPI_API_KEY is required for news research")
        from scripts.DataFetcher.serpapi_client import SerpAPIProvider
        provider = SerpAPIProvider(api_key=api_key, use_cache=config["serpapi"]["use_cache"],
                                   cache_ttl_hours=config["serpapi"]["cache_ttl_hours"])
        results = provider.search_news(query, language=language, limit=limit)
        return {"query": query, "count": len(results), "articles": [
            {k: item.get(k) for k in ("title", "url", "description", "source", "publishedAt")}
            for item in results
        ], "editorial_note": "Verify dates, original sources and claims before publication."}

    def create_script(self, title: str, source_text: str, source_url: str = "",
                      video_format: str = "short") -> dict:
        """Draft with the repo's own Chatbot. Source facts must be verified by a person."""
        if video_format not in _SUPPORTED:
            raise ValueError("video_format must be short or long")
        title = title.strip()
        source_text = source_text.strip()
        if not 5 <= len(title) <= 240 or not 30 <= len(source_text) <= 12000:
            raise ValueError("title (5-240) and source_text (30-12000) required")
        if source_url:
            from scripts.url_safety import validate_public_url
            validate_public_url(source_url)
        with _LOCK:
            config = self._config()
            bot = self._chatbot(config)
            topic = title + "\nSource material (do not invent additional facts): " + source_text[:6000]
            if video_format == "short":
                script = bot.generate_short_article(topic, source=source_url)
                summary = ""
            else:
                script, summary = bot.generate_full_article(topic)
            if not isinstance(script, str) or len(script.strip()) < 30:
                raise StudioError("LLM returned an empty or invalid script")
            project = {
                "id": uuid.uuid4().hex, "title": title, "source_text": source_text,
                "source_url": source_url, "format": video_format, "script": script.strip(),
                "summary": summary, "images": [], "voice": "", "subtitles": "",
                "video": "", "status": "draft", "video_id": "",
                "privacy": "private",
            }
            self._save(project)
            return self._public(project)

    @staticmethod
    def _public(project: dict) -> dict:
        return {key: value for key, value in project.items()
                if key not in ("approval_digest", "review_fingerprint")}

    def get_project(self, job_id: str) -> dict:
        with _LOCK:
            return self._public(self._read(job_id))

    def revise_script(self, job_id: str, script: str) -> dict:
        if len(script.strip()) < 30 or len(script) > 20000:
            raise ValueError("script must be 30-20000 characters")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            project["script"] = script.strip()
            for key, value in (("images", []), ("voice", ""), ("subtitles", ""), ("video", "")):
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
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "images": output, "prompts": prompt_list}

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
            subtitles = folder / "subtitles.srt"
            engine = TTSEdge(output_dir=str(folder))
            engine.text_to_speech_file(
                project["script"], language=voice[:2], voice=voice,
                output_path=str(audio), srt_path=str(subtitles),
            )
            if not audio.is_file() or audio.stat().st_size == 0:
                raise StudioError("TTS did not produce an audio file")
            project["voice"] = str(audio)
            project["subtitles"] = str(subtitles) if subtitles.is_file() else ""
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "voice": str(audio), "subtitles": project["subtitles"]}

    def generate_subtitles(self, job_id: str, max_words: int = 5) -> dict:
        if not 1 <= max_words <= 12:
            raise ValueError("max_words must be 1-12")
        with _LOCK:
            project = self._read(job_id)
            self._require_editable(project)
            path = Path(project["subtitles"]) if project["subtitles"] else None
            if not path or not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise StudioError("Generate Edge TTS narration with word boundaries first")
            from scripts.MediaManagers.SRT_Processor import SRTProcessor
            processor = SRTProcessor(str(path), max_words=max_words,
                                     max_duration=2.0 if project["format"] == "short" else 4.0)
            processor.process()
            if not path.stat().st_size:
                raise StudioError("Subtitle processing produced an empty SRT")
            project["video"] = ""
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "subtitles": str(path), "bytes": path.stat().st_size}

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
            output = self._dir(job_id) / "video.mp4"
            assembler = VideoAssembler(subtitle_file=str(srt), voiceover_file=str(audio),
                                       output_file=str(output), media_images=[str(p) for p in images],
                                       aspect_ratio=_SUPPORTED[project["format"]])
            assembler.assemble_video()
            if not output.is_file() or not output.stat().st_size:
                raise StudioError("FFmpeg returned no playable video")
            project["video"] = str(output)
            self._invalidate_review(project)
            self._save(project)
            return {"job_id": job_id, "video": str(output), "bytes": output.stat().st_size}

    def review_video(self, job_id: str, approve: bool = False) -> dict:
        """Review actual artifacts. approve=True yields a single-use token for PRIVATE upload."""
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
            self._invalidate_review(project)
            if approve:
                if problems:
                    raise StudioError("Resolve review issues before approval: " + "; ".join(problems))
                # This confirms editorial review by the operator, not automatic fact verification.
                code = uuid.uuid4().hex
                fingerprint = self._hash(video)
                project["review_fingerprint"] = fingerprint
                project["approval_digest"] = hashlib.sha256(code.encode()).hexdigest()
                project["status"] = "approved"
                result["approval_code"] = code
                result["status"] = "approved"
            self._save(project)
            return result

    def publish_youtube(self, job_id: str, approval_code: str) -> dict:
        """Upload only PRIVATE; never retry an uncertain upload automatically."""
        with _LOCK:
            project = self._read(job_id)
            if project["status"] == "published":
                return {"job_id": job_id, "video_id": project["video_id"],
                        "url": "https://www.youtube.com/watch?v=" + project["video_id"],
                        "privacy": "private", "already_published": True}
            if project["status"] != "approved" or not approval_code:
                raise StudioError("Editorial approval required (run review_video with approve=True)")
            provided = hashlib.sha256(approval_code.encode()).hexdigest()
            if not __import__("hmac").compare_digest(provided, project.get("approval_digest", "")):
                raise StudioError("Invalid approval code")
            video = Path(project["video"])
            if not video.is_file() or self._hash(video) != project.get("review_fingerprint"):
                raise StudioError("Video changed after approval; review again")
            config = self._config()
            secret_file = Path(config["youtube"]["credentials_file"]).resolve()
            if not secret_file.is_file():
                raise StudioError("YouTube OAuth client secrets not configured")
            secrets = Path.cwd() / ".secrets"
            secrets.mkdir(exist_ok=True)
            destination = secrets / "client_secret.json"
            if secret_file != destination.resolve():
                shutil.copy2(secret_file, destination)
            project["status"] = "uploading"
            project.pop("approval_digest", None)
            self._save(project)
            # If the request times out after YouTube accepts it, hold for reconciliation.
            try:
                from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
                uploader = YoutubeMediaUploader(client_secrets_file="client_secret.json")
                response = uploader.upload(str(video), title=project["title"][:90],
                                           description=project["summary"] or project["source_text"][:4000],
                                           tags=[], privacy_status="private")
                video_id = response.get("id")
                if not video_id:
                    raise StudioError("YouTube response lacked a video ID")
            except BaseException:
                project["status"] = "upload_unknown"
                self._save(project)
                raise
            project["video_id"] = str(video_id)
            project["status"] = "published"
            self._save(project)
            return {"job_id": job_id, "video_id": video_id,
                    "url": "https://www.youtube.com/watch?v=" + str(video_id),
                    "privacy": "private"}

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
