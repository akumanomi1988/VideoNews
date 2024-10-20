from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    TextClip,
    CompositeVideoClip
)
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.video.fx import resize, crop
import textwrap
from colorama import init, Fore
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from enum import Enum
from pydub import AudioSegment
import os

# Initialize colorama
init(autoreset=True)

# Your enums and other classes go here...

# Enums for subtitle position and style
class Position(Enum):
    TOP_LEFT = 'top_left'
    TOP_CENTER = 'top_center'
    TOP_RIGHT = 'top_right'
    MIDDLE_LEFT = 'middle_left'
    MIDDLE_CENTER = 'middle_center'
    MIDDLE_RIGHT = 'middle_right'
    BOTTOM_LEFT = 'bottom_left'
    BOTTOM_CENTER = 'bottom_center'
    BOTTOM_RIGHT = 'bottom_right'


class Style(Enum):
    DEFAULT = 'default'
    BOLD = 'bold'
    MINIMAL = 'minimal'

# ------------------ VIDEO HELPER ------------------
class VideoHelper:
    """Helper for processing video files, adjusting aspect ratios, and concatenating clips."""

    @staticmethod
    def get_target_dimensions(aspect_ratio):
        """Returns target dimensions based on the specified aspect ratio."""
        if aspect_ratio == '9:16':
            return 1080, 1920  # Vertical aspect ratio
        elif aspect_ratio == '16:9':
            return 1920, 1080  # Horizontal aspect ratio
        else:
            raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

    @staticmethod
    def adjust_aspect_ratio(clip, aspect_ratio):
        """Resizes and crops the video/image clip to match the target aspect ratio."""
        target_w, target_h = VideoHelper.get_target_dimensions(aspect_ratio)
        clip_aspect_ratio = clip.w / clip.h
        target_aspect_ratio = target_w / target_h

        if clip_aspect_ratio > target_aspect_ratio:
            resized_clip = resize.resize(clip, height=target_h)
        else:
            resized_clip = resize.resize(clip, width=target_w)

        return crop.crop(resized_clip, width=target_w, height=target_h, 
                         x_center=resized_clip.w // 2, y_center=resized_clip.h // 2)

    @staticmethod
    def process_video(file_path, aspect_ratio):
        """Processes a video file, adjusting its aspect ratio."""
        try:
            print(Fore.CYAN + f"📹 Processing video: {file_path}")
            video_clip = VideoFileClip(file_path)
            return VideoHelper.adjust_aspect_ratio(video_clip, aspect_ratio)
        except Exception as e:
            print(Fore.RED + f"❌ Error processing video {file_path}: {e}")
            return None

    @staticmethod
    def process_image(file_path, aspect_ratio):
        """Processes an image file, adjusting its aspect ratio."""
        try:
            print(Fore.CYAN + f"🖼️ Processing image: {file_path}")
            image_clip = ImageClip(file_path, duration=5)
            return VideoHelper.adjust_aspect_ratio(image_clip, aspect_ratio)
        except Exception as e:
            print(Fore.RED + f"❌ Error processing image {file_path}: {e}")
            return None


# ------------------ AUDIO HELPER ------------------
class AudioHelper:
    """Helper for processing audio files, including voiceovers and background music."""

    @staticmethod
    def get_voiceover_audio(voiceover_file):
        """Load and return the voiceover audio file."""
        try:
            audio = AudioFileClip(voiceover_file).audio_fadeout(2)
            return audio
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error loading voiceover: {e}")

    @staticmethod
    def add_background_music(video, music_file, audio_duration):
        """Add background music to a video."""
        try:
            music = AudioSegment.from_mp3(music_file)
            temp_music_file = os.path.join(".temp", "temp_music.wav")
            music.export(temp_music_file, format="wav")

            with AudioFileClip(temp_music_file) as music_clip:
                music_clip = music_clip.volumex(0.2).subclip(0, audio_duration).audio_fadeout(2)
                composite_audio = CompositeAudioClip([video.audio, music_clip])
                video = video.set_audio(composite_audio)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error processing background music: {e}")
        return video


# ------------------ IMAGE HELPER ------------------
class ImageHelper:
    """Helper for image processing, including thumbnail enhancements and image size reduction."""

    @staticmethod
    def reduce_image_size(image_path: str, max_size_kb: int, reduction_percentage: int):
        """Reduces the size of an image if it exceeds the given maximum size."""
        current_size_kb = os.path.getsize(image_path) / 1024.0
        image = Image.open(image_path)

        while current_size_kb > max_size_kb:
            width, height = image.size
            new_width = int(width * (reduction_percentage / 100.0))
            new_height = int(height * (reduction_percentage / 100.0))

            image = image.resize((new_width, new_height), Image.ANTIALIAS)
            image.save(image_path, optimize=True, quality=85)

            current_size_kb = os.path.getsize(image_path) / 1024.0
            print(f"{Fore.YELLOW}Resized to: {new_width}x{new_height}, weight: {current_size_kb:.2f} kB")

        print(f"{Fore.GREEN}Reduction complete! Image is within the size limit.")

    @staticmethod
    def enhance_thumbnail(image_path, text, position=Position.MIDDLE_CENTER, style=Style.BOLD, max_size_kb=2000, reduction_percentage=5):
        """Enhances a thumbnail by adding text in the selected position and style."""
        try:
            # Reduce image size
            ImageHelper.reduce_image_size(image_path, max_size_kb, reduction_percentage)

            # Open the image and draw text
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)

             # Configure style based on the 'style' parameter
            if style == Style.BOLD:
                font_size = 200  # Use larger text size for bold and exotic
                stroke_width = 8
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)  # Change this to a more exotic font if desired
                text_color = "yellow"  # Bright text color
                stroke_color = "black"  # Bright stroke color
            elif style == Style.MINIMAL:
                font_size = 80  # Smaller font for minimal style
                stroke_width = 0
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                text_color = "white"
                stroke_color = None
            else:  # Style.DEFAULT
                font_size = 90
                stroke_width = 3
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                text_color = "white"
                stroke_color = None

            img_width, img_height = image.size
            max_text_width = img_width * 0.8

            # Break text into multiple lines if necessary
            lines, current_line = [], ""
            for word in text.split():
                test_line = f"{current_line} {word}".strip()
                if draw.textsize(test_line, font=font)[0] <= max_text_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Calculate starting position
            total_text_height = sum([draw.textsize(line, font=font)[1] for line in lines])
            line_height = font.getsize(lines[0])[1]
            text_position = ImageHelper.calculate_text_position(position, img_width, img_height, max_text_width, total_text_height)

            for line in lines:
                if stroke_width > 0:
                    draw.text(text_position, line, fill=text_color, stroke_fill=stroke_color, stroke_width=stroke_width, font=font)
                else:
                    draw.text(text_position, line, fill=text_color, font=font)
                text_position = (text_position[0], text_position[1] + line_height)  # Move down for next line

            # Overwrite the original image
            image.save(image_path)  # Save back to the original path
            print(Fore.GREEN + f"✅ Thumbnail updated: {image_path}")

        except Exception as e:
            print(Fore.RED + f"❌ Error enhancing thumbnail: {e}")

    @staticmethod
    def calculate_text_position(position, img_width, img_height, max_text_width, total_text_height):
        """Calculate text position based on enum."""
        if position == Position.TOP_LEFT:
            return (int(0.1 * img_width), int(0.1 * img_height))
        elif position == Position.TOP_CENTER:
            return ((img_width - max_text_width) // 2, int(0.1 * img_height))
        elif position == Position.TOP_RIGHT:
            return (img_width - max_text_width - 20, int(0.1 * img_height))
        elif position == Position.MIDDLE_LEFT:
            return (int(0.1 * img_width), (img_height - total_text_height) // 2)
        elif position == Position.MIDDLE_CENTER:
            return ((img_width - max_text_width) // 2, (img_height - total_text_height) // 2)
        elif position == Position.MIDDLE_RIGHT:
            return (img_width - max_text_width - 20, (img_height - total_text_height) // 2)
        elif position == Position.BOTTOM_LEFT:
            return (int(0.1 * img_width), img_height - total_text_height - 20)
        elif position == Position.BOTTOM_CENTER:
            return ((img_width - max_text_width) // 2, img_height - total_text_height - 20)
        elif position == Position.BOTTOM_RIGHT:
            return (img_width - max_text_width - 20, img_height - total_text_height - 20)

# ------------------ SUBTITLE HELPER ------------------
class SubtitleHelper:
    @staticmethod
    def split_subtitles(subtitle_text):
        """Split long subtitles into shorter lines for better readability."""
        return '\n'.join(textwrap.wrap(subtitle_text, width=150))

    @staticmethod
    def generate_subtitle(txt, video_size, 
                          position=Position.MIDDLE_CENTER,
                          style=Style.BOLD,
                          bg_color=None,
                          text_color='yellow'):
        """
        Generate subtitles with customizable styles and positioning.
        """
        txt = SubtitleHelper.split_subtitles(txt)  # Split long subtitles

        if style == Style.BOLD:
            font = 'Impact'
            fontsize = 150
            stroke_color = 'black'
            stroke_width = 5
        elif style == Style.MINIMAL:
            font = 'Arial'
            fontsize = 100
            stroke_color = None
            stroke_width = 0
            bg_color = None
        else:
            font = 'Helvetica'
            fontsize = 120
            stroke_color = 'black'
            stroke_width = 3

        text_clip = TextClip(
            txt,
            font=font,
            fontsize=fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(video_size[0] - 100, None),
            align='center'
        )

        text_width, text_height = text_clip.size
        padding_x = 20
        padding_y = 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y

        max_height = video_size[1] / 3
        if text_height > max_height:
            scale_factor = max_height / text_height
            text_clip = text_clip.resize(newsize=(int(text_width * scale_factor), int(max_height)))

        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=(0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)
        else:
            image_clip = None

        # Ajustar la posición según el nuevo enum
        if position == Position.TOP_LEFT:
            final_position = (0.1 * video_size[0], 0.1 * video_size[1])
        elif position == Position.TOP_CENTER:
            final_position = ('center', 0.1 * video_size[1])
        elif position == Position.TOP_RIGHT:
            final_position = (0.9 * video_size[0], 0.1 * video_size[1])
        elif position == Position.MIDDLE_LEFT:
            final_position = (0.1 * video_size[0], 'center')
        elif position == Position.MIDDLE_CENTER:
            final_position = ('center', 'center')
        elif position == Position.MIDDLE_RIGHT:
            final_position = (0.9 * video_size[0], 'center')
        elif position == Position.BOTTOM_LEFT:
            final_position = (0.1 * video_size[0], 0.8 * video_size[1])
        elif position == Position.BOTTOM_CENTER:
            final_position = ('center', 0.8 * video_size[1])
        elif position == Position.BOTTOM_RIGHT:
            final_position = (0.9 * video_size[0], 0.8 * video_size[1])

        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip

    @staticmethod
    def add_subtitles(video, subtitle_file, style=Style.DEFAULT, position=Position.MIDDLE_CENTER):
        """Add subtitles to the video based on the provided subtitle file."""
        try:
            subtitles = SubtitlesClip(subtitle_file, lambda txt: SubtitleHelper.generate_subtitle(txt, video.size, style=style, position=position))
            subtitles = subtitles.set_position(('center', 'center'))
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")