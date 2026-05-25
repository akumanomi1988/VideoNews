import os
import textwrap
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw
from colorama import init, Fore

from typing import List, Optional, Dict
import logging
import moviepy.editor as mp
from pathlib import Path
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import (
    TextClip, CompositeVideoClip, ImageClip, VideoFileClip
)
from moviepy.video.fx import resize, crop

import gc
import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper
from .interfaces import VideoAssembler as VideoAssemblerInterface, VideoMetadata
from .utils.app_logger import trace
from AkumaImageEffect.effect_engine import AkumaEngine, EffectConfig
import AkumaImageEffect.effects.core_effects  # Registers zoom effects
try:
    from AkumaSubtitler import AkumaSubtitler
except ModuleNotFoundError:
    from akumasubtitler import AkumaSubtitler

# Initialize colorama for colored terminal output
init(autoreset=True)

# Constants for configuration and supported formats
SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
DEFAULT_FPS = 30
DEFAULT_BG_COLOR = (255, 255, 255)
DEFAULT_INTERPOLATION = cv2.INTER_CUBIC

class VideoAssemblerError(Exception):
    """Custom exception for video assembly errors"""
    pass

class ResourceManager:
    """Manages video processing resources and cleanup"""
    
    @trace()
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

    @trace()
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

    @trace()
    def get_target_dimensions(self) -> Tuple[int, int]:
        """
        Return target dimensions based on the specified aspect ratio.
        """
        if self.aspect_ratio == '9:16':
            return 1080, 1920
        elif self.aspect_ratio == '16:9':
            return 1920, 1080
        raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

    @trace()
    def adjust_aspect_ratio(self, clip: VideoFileClip) -> VideoFileClip:
        """
        Resize and crop the video/image clip to match the target aspect ratio.
        """
        target_w, target_h = self.get_target_dimensions()
        clip_aspect_ratio = clip.w / clip.h
        target_aspect_ratio = target_w / target_h

        if clip_aspect_ratio > target_aspect_ratio:
            resized_clip = resize.resize(clip, height=target_h)
        else:
            resized_clip = resize.resize(clip, width=target_w)

        cropped_clip = crop.crop(
            resized_clip,
            width=target_w,
            height=target_h,
            x_center=resized_clip.w // 2,
            y_center=resized_clip.h // 2
        )
        return cropped_clip

    def process_video_files(self) -> List[VideoFileClip]:
        """
        Process and adjust video files to match the aspect ratio.
        """
        adjusted_clips = []
        for media_file in self.media_videos:
            try:
                print(Fore.CYAN + f"📹 Processing video: {media_file}")
                video_clip = VideoFileClip(media_file)
                adjusted_clips.append(self.adjust_aspect_ratio(video_clip))
            except Exception as e:
                print(Fore.RED + f"❌ Error processing video {media_file}: {e}")
        return adjusted_clips

    def process_image_files(self, audio_duration: float) -> List[VideoFileClip]:
        """
        Process and convert images to video clips with effects, matching the aspect ratio.
        """
        adjusted_clips = []
        config = EffectConfig(
            background_color=DEFAULT_BG_COLOR,
            interpolation=DEFAULT_INTERPOLATION
        )
        num_images = len(self.media_images)
        if num_images == 0:
            return adjusted_clips

        duration_per_image = audio_duration / num_images

        for image_file in self.media_images:
            if not self._is_valid_image_file(image_file):
                continue
            try:
                self._verify_image_integrity(image_file)
                output_path = self._generate_video_from_image(
                    image_file, config, duration_per_image
                )
                video_clip = VideoFileClip(output_path)
                adjusted_clips.append(self.adjust_aspect_ratio(video_clip))
            except Exception as e:
                print(Fore.RED + f"❌ Error processing image {image_file}: {e}")
        return adjusted_clips

    def _is_valid_image_file(self, image_file: str) -> bool:
        """
        Check if the image file exists and has a supported format.
        """
        if not os.path.isfile(image_file):
            print(Fore.YELLOW + f"⚠️ File not found: {image_file}. Skipping.")
            return False
        if not image_file.lower().endswith(SUPPORTED_IMAGE_FORMATS):
            print(Fore.YELLOW + f"⚠️ Unsupported image format: {image_file}. Skipping.")
            return False
        return True

    def _verify_image_integrity(self, image_file: str) -> None:
        """
        Verify that the image is not corrupt or unreadable.
        """
        try:
            with Image.open(image_file) as img:
                img.verify()
        except Exception:
            raise ValueError(f"⚠️ Corrupt or unreadable image: {image_file}. Skipping.")

    def _generate_video_from_image(
        self, image_file: str, config: EffectConfig, duration: float
    ) -> str:
        """
        Generate a video from an image using AkumaEngine.
        """
        engine = AkumaEngine(config)
        output_path = os.path.splitext(image_file)[0] + ".mp4"
        effect = "akuma_zoom_in"
        try:
            engine.generate_video(
                image_src=image_file,
                effect=effect,
                duration=duration,
                output_path=output_path,
                fps=DEFAULT_FPS
            )
            print(f"Video successfully generated: {output_path}")
        except Exception as e:
            raise RuntimeError(f"Error generating video: {e}")
        return output_path

    def adjust_media(self) -> List[VideoFileClip]:
        """
        Process and adjust all media files (videos and images) to match the aspect ratio.
        """
        audio_duration = mp.AudioFileClip(self.voiceover_file).duration
        video_clips = self.process_video_files()
        image_clips = self.process_image_files(audio_duration)
        return video_clips + image_clips

    def split_subtitles(self, subtitle_text: str, width: int = 15) -> str:
        """
        Split long subtitles into shorter lines for better readability.
        """
        return '\n'.join(textwrap.wrap(subtitle_text, width=width))

    @trace()
    def assemble_video(
        self,
        style: Style = Style.DEFAULT,
        position: Position = Position.MIDDLE_CENTER
    ) -> None:
        """
        Assemble and create the final video with subtitles, voiceover, and optional background music.
        """
        adjusted_clips = self.adjust_media()
        if not adjusted_clips:
            raise ValueError(Fore.RED + "🚨 No media files could be adjusted. Check your inputs.")

        video = self._concatenate_clips(adjusted_clips)
        audio = self._load_voiceover_audio()
        video = video.set_audio(audio)

        if self.background_music:
            video = self._add_background_music(video, audio)

        if self.subtitle_file:
            video = self._add_subtitles(video, style, position)
            self._write_final_video(video, audio.duration)
        else:
            self._write_final_video(video, audio.duration)
            # Initialize the subtitler
            akuma = AkumaSubtitler()
            # Basic usage with auto-generated subtitles
            akuma.forge_video(
                video_path=self.output_file,
                output_path=self.output_file
            )



    def _concatenate_clips(self, clips: List[VideoFileClip]) -> CompositeVideoClip:
        """
        Concatenate video clips into a single video.
        """
        try:
            return mp.concatenate_videoclips(clips)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error concatenating video clips: {e}")

    def _load_voiceover_audio(self) -> mp.AudioFileClip:
        """
        Load the voiceover audio file and apply fadeout.
        """
        try:
            return mp.AudioFileClip(self.voiceover_file).audio_fadeout(2)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error loading voiceover: {e}")

    def _add_background_music(
        self, video: CompositeVideoClip, voiceover_audio: mp.AudioFileClip
    ) -> CompositeVideoClip:
        """
        Add background music to the video, mixing it with the voiceover.
        """
        try:
            music = mp.AudioFileClip(self.background_music)
            background_audio = mp.CompositeAudioClip([
                voiceover_audio, music.volumex(0.2)
            ])
            return video.set_audio(background_audio)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error processing background music: {e}")

    def _add_subtitles(
        self, video: CompositeVideoClip, style: Style, position: Position
    ) -> CompositeVideoClip:
        """
        Add subtitles to the video at the specified position and style.
        """
        try:
            final_position = SubtitleHelper.calculate_text_position_video(
                position=position,
                img_width=video.size[0],
                img_height=video.size[1],
                max_text_width=0.95 * video.size[0],
                total_text_height=video.size[1] / 3
            )
            subtitles = SubtitlesClip(
                self.subtitle_file,
                lambda txt: self.generate_subtitle(txt, video.size, style=style, position=position)
            ).set_position(final_position)
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")

    def _write_final_video(self, video: CompositeVideoClip, duration: float) -> None:
        """
        Write the final video file to disk.
        """
        try:
            end_time = min(duration, video.duration)
            final_video = video.subclip(0, end_time).fadeout(2)
            final_video.write_videofile(self.output_file, write_logfile=False)
            print(Fore.GREEN + "✅ Video processing completed successfully.")
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error writing final video: {e}")

    def generate_subtitle(
        self,
        txt: str,
        video_size: Tuple[int, int],
        position: Position = Position.MIDDLE_CENTER,
        style: Style = Style.BOLD,
        bg_color: Optional[str] = None,
        text_color: str = 'yellow'
    ) -> CompositeVideoClip:
        """
        Generate a styled subtitle clip for overlaying on the video.
        """
        txt = txt.encode('utf-8').decode('utf-8')
        style_params = SubtitleHelper.get_style_parameters(style)
        font = style_params['font_path']
        fontsize = style_params['fontsize']
        stroke_color = style_params['stroke_color']
        stroke_width = style_params['stroke_width']
        text_color = style_params['text_color']
        bg_color = style_params['bg_color']

        text_clip = TextClip(
            txt,
            font=font,
            fontsize=fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(video_size[0] * 0.9, None),
            align='center',
        )

        text_width, text_height = text_clip.size
        padding_x, padding_y = 20, 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y

        max_height = video_size[1] / 3
        if text_height > max_height:
            scale_factor = max_height / text_height
            text_clip = text_clip.resize(newsize=(int(text_width * scale_factor), int(max_height)))
            box_width = int(text_width * scale_factor) + 2 * padding_x
            box_height = int(max_height) + 2 * padding_y

        image_clip = None
        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25
            fill_color = (0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=fill_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)

        final_position = SubtitleHelper.calculate_text_position_video(
            position=position,
            img_width=video_size[0],
            img_height=video_size[1],
            max_text_width=0.8 * video_size[0],
            total_text_height=max_height
        )

        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip

    def _check_memory_requirements(self):
        """Check if system has enough memory for video processing"""
        memory = psutil.virtual_memory()
        if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB minimum
            self.logger.warning("Low memory available, performance may be affected")

    @trace()
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
                lambda txt: self.generate_subtitle(
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

