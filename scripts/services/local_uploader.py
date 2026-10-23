"""Local publishing adapter: keep artifacts when upload is not explicitly enabled."""

import json
import shutil
import uuid
from pathlib import Path
from ..interfaces import VideoUploader, VideoMetadata


class LocalVideoUploader(VideoUploader):
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def upload(self, video_path: str, metadata: VideoMetadata) -> str:
        source = Path(video_path)
        if not source.is_file():
            raise FileNotFoundError(f"Rendered video was not created: {source}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        dest = self.output_dir / f"{uuid.uuid4().hex[:10]}_{source.name}"
        shutil.copy2(source, dest)
        sidecar = dest.with_suffix(".json")
        sidecar.write_text(json.dumps({
            "title": metadata.title, "description": metadata.description,
            "tags": metadata.tags
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        if metadata.thumbnail_path and Path(metadata.thumbnail_path).is_file():
            shutil.copy2(metadata.thumbnail_path, dest.with_suffix(".jpg"))
        return str(dest.resolve())
