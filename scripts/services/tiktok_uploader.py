"""TikTok publishing is deliberately disabled until a real OAuth flow exists."""
from ..interfaces import VideoUploader, VideoMetadata


class TiktokUploader(VideoUploader):
    def __init__(self, session_file=None):
        raise NotImplementedError(
            "TikTok OAuth is not configured. Select local or YouTube output instead."
        )

    def upload(self, video_path: str, metadata: VideoMetadata) -> str:
        raise NotImplementedError("TikTok publishing is not implemented")
