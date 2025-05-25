import os
import textwrap
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw
from colorama import init, Fore
from pydub import AudioSegment
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import (
    TextClip, CompositeVideoClip, ImageClip, VideoFileClip
)
from moviepy.video.fx import resize, crop

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper
from AkumaImageEffect.effect_engine import AkumaEngine, EffectConfig
import AkumaImageEffect.effects.core_effects  # Auto-imports and registers effects

# Initialize colorama for colored terminal output
init(autoreset=True)

# Constants for configuration and supported formats
SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
DEFAULT_FPS = 30
DEFAULT_BG_COLOR = (255, 255, 255)
DEFAULT_INTERPOLATION = cv2.INTER_CUBIC

class VideoAssembler:
    """
    Class responsible for assembling a video from images/videos, voiceover, subtitles, and optional background music.
    """
    def __init__(
        self,
        subtitle_file: str,
        voiceover_file: str,
        output_file: str,
        media_videos: Optional[List[str]] = None,
        media_images: Optional[List[str]] = None,
        aspect_ratio: str = "9:16",
        background_music: str = ""
    ):
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.media_videos = media_videos or []
        self.media_images = media_images or []
        self.aspect_ratio = aspect_ratio
        self.background_music = background_music

    def get_target_dimensions(self) -> Tuple[int, int]:
        """
        Return target dimensions based on the specified aspect ratio.
        """
        if self.aspect_ratio == '9:16':
            return 1080, 1920
        elif self.aspect_ratio == '16:9':
            return 1920, 1080
        raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

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
            final_video = video.subclip(0, duration).fadeout(2)
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

# --- Main execution block for testing/demo purposes ---

if __name__ == "__main__":
    # Configuration constants for demo/testing
    SUBTITLE_FILE = "scripts/.temp/subtitles.srt"
    VOICEOVER_FILE = ".temp/c6f3db91-5d9a-4db5-8d33-4a22039bb973.mp3"
    OUTPUT_FILE = ".temp/Análisis_de_los_Siete_Estados_C2.mp4"
    MEDIA_IMAGES = [
        ".temp/NONE_8f38d792-7e26-4eac-9e39-3476fb47ed30.png",
        ".temp/NONE_af2e1d86-dffb-4ebe-a193-8aca7d2c51bc.png",
        ".temp/NONE_058309ef-7531-4093-971c-d65578544e3e.png",
        ".temp/NONE_2a737ae5-7d13-4835-8cb2-cc318a0f2445.png"
    ]
    MEDIA_VIDEOS = []
    BACKGROUND_MUSIC = "Resources/Music/SweetBananaMelody.mp3"
    ASPECT_RATIO = "16:9"

    # Example: Enhance thumbnail (for demonstration)
    ImageHelper.enhance_thumbnail(
        ".temp/NONE_6ffe59f0-6917-48ca-aae1-d960230c69a2.png",
        "El increible titular está guapísimo para esta noticia impresionante",
        Position.BOTTOM_CENTER,
        Style.THUMBNAIL_BOLD,
        2000,
        95
    )

    # Create and run the video assembler
    video_assembler = VideoAssembler(
        subtitle_file=SUBTITLE_FILE,
        voiceover_file=VOICEOVER_FILE,
        output_file=OUTPUT_FILE,
        media_images=MEDIA_IMAGES,
        media_videos=MEDIA_VIDEOS,
        background_music=BACKGROUND_MUSIC,
        aspect_ratio=ASPECT_RATIO
    )
    video_assembler.assemble_video(style=Style.BOLD, position=Position.BOTTOM_CENTER)

