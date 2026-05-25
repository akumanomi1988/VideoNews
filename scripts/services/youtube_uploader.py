import os
import shutil
from typing import Optional
import logging

from ..interfaces import VideoUploader, VideoMetadata
from ..Uploaders.youtube_uploader import YoutubeMediaUploader as YoutubeMediaUploaderImpl
from ..utils.app_logger import trace


class YoutubeUploader(VideoUploader):
    """Adapter that wraps YoutubeMediaUploader for the VideoUploader protocol"""

    @trace()
    def __init__(self, credentials_path: str, client_secrets_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        secrets_file = client_secrets_path or credentials_path

        # Copy secrets file to .secrets/ if needed (YoutubeMediaUploader expects it there)
        secrets_dir = os.path.join(os.getcwd(), ".secrets")
        os.makedirs(secrets_dir, exist_ok=True)
        target = os.path.join(secrets_dir, "client_secret.json")
        if os.path.exists(secrets_file) and not os.path.exists(target):
            shutil.copy2(secrets_file, target)
            self.logger.info(f"Copied {secrets_file} to {target}")

        self._uploader = YoutubeMediaUploaderImpl(client_secrets_file="client_secret.json")

    @trace()
    def upload(self, video_path: str, metadata: VideoMetadata) -> str:
        response = self._uploader.upload(
            video_path=video_path,
            title=metadata.title,
            description=metadata.description,
            tags=metadata.tags,
            thumbnail_path=metadata.thumbnail_path,
        )
        video_id = response.get("id", "")
        return f"https://www.youtube.com/watch?v={video_id}"
