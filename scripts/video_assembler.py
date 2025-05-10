from typing import List, Optional, Dict
import logging
import moviepy.editor as mp
from pathlib import Path
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import CompositeVideoClip, VideoFileClip, ImageClip, AudioFileClip
import psutil
import gc
import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper
from .interfaces import VideoAssembler as VideoAssemblerInterface, VideoMetadata

class VideoAssemblerError(Exception):
    """Custom exception for video assembly errors"""
    pass

class ResourceManager:
    """Manages video processing resources and cleanup"""
    
    def __init__(self):
        self.clips = []
        self.audio_clips = []
        self.logger = logging.getLogger(__name__)

    def register_clip(self, clip):
        """Register a clip for cleanup"""
        self.clips.append(clip)
        return clip

    def register_audio(self, audio):
        """Register an audio clip for cleanup"""
        self.audio_clips.append(audio)
        return audio

    def cleanup(self):
        """Clean up all registered resources"""
        for clip in self.clips:
            try:
                clip.close()
            except Exception as e:
                self.logger.warning(f"Error closing clip: {e}")

        for audio in self.audio_clips:
            try:
                audio.close()
            except Exception as e:
                self.logger.warning(f"Error closing audio: {e}")

        self.clips.clear()
        self.audio_clips.clear()
        gc.collect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

class VideoAssembler(VideoAssemblerInterface):
    """Handles video assembly with memory management"""

    def __init__(
        self,
        subtitle_file: Optional[str] = None,
        voiceover_file: Optional[str] = None,
        output_file: Optional[str] = None,
        media_images: Optional[List[str]] = None,
        media_videos: Optional[List[str]] = None,
        aspect_ratio: str = "16:9",
        background_music: Optional[str] = None
    ):
        self.logger = logging.getLogger(__name__)
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.media_images = media_images or []
        self.media_videos = media_videos or []
        self.aspect_ratio = aspect_ratio
        self.background_music = background_music
        self.subtitle_helper = SubtitleHelper()
        self._check_memory_requirements()

    def _check_memory_requirements(self):
        """Check if system has enough memory for video processing"""
        memory = psutil.virtual_memory()
        if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB minimum
            self.logger.warning("Low memory available, performance may be affected")

    def assemble(
        self,
        media_paths: List[str],
        audio_path: str,
        subtitles_path: str,
        metadata: VideoMetadata
    ) -> str:
        """Assemble video with resource management"""
        with ResourceManager() as resources:
            try:
                self.logger.info("Starting video assembly...")
                
                # Update instance paths
                self.media_images = media_paths
                self.voiceover_file = audio_path
                self.subtitle_file = subtitles_path
                self.output_file = str(Path(audio_path).parent / f"{metadata.title[:50]}.mp4")

                # Process media files in parallel
                adjusted_clips = self._process_media_files(resources)
                if not adjusted_clips:
                    raise VideoAssemblerError("No valid media files to process")

                # Combine clips
                video = resources.register_clip(self._combine_clips(adjusted_clips))
                if not video:
                    raise VideoAssemblerError("Failed to combine video clips")

                # Add audio with resource management
                video = self._add_audio(video, resources)

                # Add subtitles
                video = self._add_subtitles(video)

                # Write final video
                self._write_video(video)

                return self.output_file

            except Exception as e:
                self.logger.error(f"Video assembly failed: {e}")
                raise VideoAssemblerError(f"Failed to assemble video: {e}")

    def _process_media_files(self, resources: ResourceManager):
        """Process media files with parallel processing"""
        adjusted_clips = []
        
        try:
            # Get audio duration for timing
            audio = resources.register_audio(mp.AudioFileClip(self.voiceover_file))
            audio_duration = audio.duration
            clip_duration = audio_duration / (len(self.media_images) or 1)

            # Process files in parallel
            with ThreadPoolExecutor(max_workers=min(4, len(self.media_images))) as executor:
                future_to_file = {
                    executor.submit(
                        self._create_clip_from_media,
                        media_file,
                        clip_duration,
                        resources
                    ): media_file for media_file in self.media_images
                }
                
                for future in as_completed(future_to_file):
                    media_file = future_to_file[future]
                    try:
                        clip = future.result()
                        if clip:
                            adjusted_clips.append(clip)
                    except Exception as e:
                        self.logger.warning(f"Failed to process {media_file}: {e}")

            return adjusted_clips
        except Exception as e:
            self.logger.error(f"Failed to process media files: {e}")
            raise

    def _create_clip_from_media(self, media_file: str, duration: float, resources: ResourceManager):
        """Create and adjust a clip from media file"""
        try:
            if media_file.lower().endswith(('.mp4', '.avi', '.mov')):
                clip = resources.register_clip(VideoFileClip(media_file))
            else:
                clip = resources.register_clip(ImageClip(media_file).set_duration(duration))

            return self._adjust_aspect_ratio(clip)
        except Exception as e:
            self.logger.error(f"Failed to create clip from {media_file}: {e}")
            return None

    def _adjust_aspect_ratio(self, clip):
        """Adjust clip to target aspect ratio"""
        try:
            target_w, target_h = self._get_dimensions()
            clip_ratio = clip.w / clip.h
            target_ratio = target_w / target_h

            if clip_ratio > target_ratio:
                clip = clip.resize(height=target_h)
            else:
                clip = clip.resize(width=target_w)

            # Crop to exact dimensions
            x_center = clip.w // 2
            y_center = clip.h // 2
            return clip.crop(
                x_center=x_center,
                y_center=y_center,
                width=target_w,
                height=target_h
            )
        except Exception as e:
            self.logger.error(f"Failed to adjust aspect ratio: {e}")
            raise

    def _get_dimensions(self) -> tuple:
        """Get target dimensions based on aspect ratio"""
        if self.aspect_ratio == "16:9":
            return 1920, 1080
        elif self.aspect_ratio == "9:16":
            return 1080, 1920
        else:
            return 1920, 1080  # Default to 16:9

    def _combine_clips(self, clips: List[mp.VideoClip]) -> mp.VideoClip:
        """Combine clips into single video"""
        try:
            return mp.concatenate_videoclips(clips, method="compose")
        except Exception as e:
            self.logger.error(f"Failed to combine clips: {e}")
            raise

    def _add_audio(self, video: mp.VideoClip, resources: ResourceManager) -> mp.VideoClip:
        """Add audio to video"""
        try:
            audio = mp.AudioFileClip(self.voiceover_file)
            
            if self.background_music:
                bg_music = mp.AudioFileClip(self.background_music)
                bg_music = bg_music.volumex(0.1)  # Lower background volume
                audio = mp.CompositeAudioClip([audio, bg_music])

            return video.set_audio(audio)
        except Exception as e:
            self.logger.error(f"Failed to add audio: {e}")
            raise

    def _add_subtitles(self, video: mp.VideoClip) -> mp.VideoClip:
        """Add subtitles to video"""
        if not self.subtitle_file:
            return video

        try:
            position = Position.BOTTOM_CENTER if self.aspect_ratio == "16:9" else Position.MIDDLE_CENTER
            style = Style.FORMAL if self.aspect_ratio == "16:9" else Style.DEFAULT
            
            subtitles = SubtitlesClip(
                self.subtitle_file,
                lambda txt: self.subtitle_helper.generate_subtitle(
                    txt,
                    video.size,
                    position=position,
                    style=style
                )
            )
            
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            self.logger.error(f"Failed to add subtitles: {e}")
            raise

    def _write_video(self, video: mp.VideoClip) -> None:
        """Write final video file"""
        try:
            video.write_videofile(
                self.output_file,
                codec='libx264',
                audio_codec='aac',
                fps=24,
                threads=4,
                write_logfile=False
            )
            self.logger.info(f"Video saved to: {self.output_file}")
        except Exception as e:
            self.logger.error(f"Failed to write video: {e}")
            raise

