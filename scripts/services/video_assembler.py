from typing import List, Optional
from scripts.video_assembler import VideoAssembler as VideoAssemblerImpl
from scripts.video_assembler import ResourceManager, VideoAssemblerError
from ..interfaces import VideoAssembler as VideoAssemblerInterface, VideoMetadata
from ..utils.app_logger import trace

import logging


class VideoAssembler(VideoAssemblerInterface):
    """Adapter that wraps the refactored VideoAssembler for the new pipeline"""

    @trace()
    def __init__(
        self,
        subtitle_file: Optional[str] = None,
        voiceover_file: Optional[str] = None,
        output_file: Optional[str] = None,
        media_images: Optional[List[str]] = None,
        media_videos: Optional[List[str]] = None,
        aspect_ratio: str = "16:9",
        background_music: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self._impl: Optional[VideoAssemblerImpl] = None
        self._init_kwargs = {
            "subtitle_file": subtitle_file,
            "voiceover_file": voiceover_file,
            "output_file": output_file,
            "media_images": media_images,
            "media_videos": media_videos,
            "aspect_ratio": aspect_ratio,
            "background_music": background_music,
        }

    @trace()
    def assemble(
        self, media_paths: List[str], audio_path: str, subtitles_path: str, metadata: VideoMetadata
    ) -> str:
        self._impl = VideoAssemblerImpl(
            subtitle_file=subtitles_path,
            voiceover_file=audio_path,
            output_file=str(audio_path).rsplit(".", 1)[0] + ".mp4",
            media_images=media_paths,
            aspect_ratio=self._init_kwargs.get("aspect_ratio", "16:9"),
            background_music=self._init_kwargs.get("background_music"),
        )
        self._impl.assemble(
            media_paths=media_paths,
            audio_path=audio_path,
            subtitles_path=subtitles_path,
            metadata=metadata,
        )
        return self._impl.output_file
