from typing import Optional
import logging

from ..interfaces import VideoUploader, VideoMetadata
from ..Uploaders.tiktok_uploader import TiktokMediaUploader as TiktokMediaUploaderImpl
from ..utils.app_logger import trace


class TiktokUploader(VideoUploader):
    """Adapter that wraps TiktokMediaUploader for the VideoUploader protocol"""

    @trace()
    def __init__(self, session_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self._uploader = TiktokMediaUploaderImpl(
            client_id="",
            client_secret="",
            redirect_uri="",
        )

    @trace()
    def upload(self, video_path: str, metadata: VideoMetadata) -> str:
        self._uploader.upload_media(video_path)
        return ""
