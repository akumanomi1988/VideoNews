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
    ELEGANT = 'elegant'
    VIBRANT = 'vibrant'
    CASUAL = 'casual'
    SUBTLE = 'subtle'
    FORMAL = 'formal'
    DRAMATIC = 'dramatic'
    THUMBNAIL_BOLD = 'thumbnail_bold'
    THUMBNAIL_MINIMAL = 'thumbnail_minimal'
    THUMBNAIL_ELEGANT = 'thumbnail_elegant'
    THUMBNAIL_VIBRANT = 'thumbnail_vibrant'
    THUMBNAIL_CASUAL = 'thumbnail_casual'
    THUMBNAIL_CARTOON = 'thumbnail_cartoon'
    THUMBNAIL_INTENSA = 'thumbnail_intensa'


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
    def process_image(file_path, aspect_ratio, audio_duration, num_images):
        """Processes an image file, adjusting its aspect ratio and setting its duration."""
        try:
            print(Fore.CYAN + f"🖼️ Processing image: {file_path}")
            image_clip = ImageClip(file_path)
            adjusted_clip = VideoHelper.adjust_aspect_ratio(image_clip, aspect_ratio)

            # Calculate duration for each image
            image_duration = audio_duration / num_images
            return adjusted_clip.set_duration(image_duration)
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
        """Reduces the size of an image if it exceeds the given maximum size.
        
        Args:
            image_path: Path to the image file
            max_size_kb: Maximum size in KB for the output image
            reduction_percentage: Percentage to reduce dimensions by in each iteration
            
        The function will progressively reduce the image size until it's under max_size_kb,
        maintaining aspect ratio and image quality as much as possible.
        """
        import os
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"{Fore.RED}❌ Image file not found: {image_path}")
        if reduction_percentage <= 0 or reduction_percentage >= 100:
            raise ValueError(f"{Fore.RED}❌ Reduction percentage must be between 1 and 99")
        current_size_kb = os.path.getsize(image_path) / 1024.0
        if current_size_kb <= max_size_kb:
            print(f"{Fore.GREEN}✅ Image already within size limit: {current_size_kb:.2f} KB")
            return
        try:
            image = Image.open(image_path)
            original_format = image.format
            quality = 95
            attempts = 0
            max_attempts = 10  # Prevent infinite loops
            while current_size_kb > max_size_kb and attempts < max_attempts:
                attempts += 1
                width, height = image.size
                if attempts > 1:
                    scale = (100 - reduction_percentage) / 100.0
                    new_width = max(int(width * scale), 1)
                    new_height = max(int(height * scale), 1)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                image.save(image_path, format=original_format, optimize=True, quality=quality)
                current_size_kb = os.path.getsize(image_path) / 1024.0
                if current_size_kb > max_size_kb and quality > 65:
                    quality -= 5
                print(f"{Fore.YELLOW}📏 Size: {current_size_kb:.2f} KB, "
                      f"Dimensions: {image.size[0]}x{image.size[1]}, "
                      f"Quality: {quality}%")
            if current_size_kb <= max_size_kb:
                print(f"{Fore.GREEN}✅ Image successfully reduced to {current_size_kb:.2f} KB")
            else:
                print(f"{Fore.YELLOW}⚠️ Could not reduce image below {max_size_kb} KB "
                      f"while maintaining acceptable quality")
        except Exception as e:
            print(f"{Fore.RED}❌ Error reducing image size: {str(e)}")
            raise

    @staticmethod
    def enhance_thumbnail(image_path: str, text: str, 
                      position: Position = Position.MIDDLE_CENTER, 
                      style: Style = Style.THUMBNAIL_BOLD, 
                      max_size_kb: int = 2000, 
                      reduction_percentage: int = 5, 
                      text_size: int = 0):
        """Enhances a thumbnail by adding text in the selected position and style.
        
        Args:
            image_path: Path to the image file
            text: Text to add to the image
            position: Position enum indicating where to place the text
            style: Style enum indicating the text style to use
            max_size_kb: Maximum size in KB for the output image
            reduction_percentage: Percentage to reduce image by if over max_size_kb
            text_size: Optional custom text size, as percentage of default size
        """
        try:
            ImageHelper.reduce_image_size(image_path, max_size_kb, reduction_percentage)
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            style_params = SubtitleHelper.get_style_parameters(style)
            font_path = style_params['font_path']
            font_size = text_size if text_size > 0 else style_params['fontsize']
            stroke_color = style_params['stroke_color']
            stroke_width = style_params['stroke_width']
            text_color = style_params['text_color']
            img_width, img_height = image.size
            max_text_width = int(img_width * 0.6)
            font = ImageFont.truetype(font_path, font_size)
            lines = []
            words = text.split()
            current_line = words[0] if words else ""
            for word in words[1:]:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                if line_width <= max_text_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
            line_heights = []
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_heights.append(bbox[3] - bbox[1])
            total_text_height = sum(line_heights)
            line_spacing = int(font_size * 0.2)
            total_height_with_spacing = total_text_height + (line_spacing * (len(lines) - 1))
            text_position = SubtitleHelper.calculate_text_position_image(
                position, img_width, img_height, max_text_width, total_height_with_spacing
            )
            current_y = text_position[1]
            for idx, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                centered_x = text_position[0] + (max_text_width - line_width) // 2
                if stroke_width and stroke_width > 0:
                    draw.text((centered_x, current_y), line, fill=text_color, 
                              stroke_fill=stroke_color, stroke_width=stroke_width, 
                              font=font, align='center')
                else:
                    draw.text((centered_x, current_y), line, fill=text_color, 
                              font=font, align='center')
                current_y += line_heights[idx] + line_spacing
            image.save(image_path)
            print(Fore.GREEN + f"✅ Thumbnail updated: {image_path}")
        except Exception as e:
            print(Fore.RED + f"❌ Error enhancing thumbnail: {e}")

# ------------------ SUBTITLE HELPER ------------------
class SubtitleHelper:
    @staticmethod
    def calculate_text_position_image(position, img_width, img_height, max_text_width, text_height):
        """Calculate text position with a 10% margin."""
        # Definir los márgenes del 10% de la imagen
        margin_x = int(0.1 * img_width)
        margin_y = int(0.1 * img_height)

        if position == Position.TOP_LEFT:
            return (margin_x, margin_y)
        elif position == Position.TOP_CENTER:
            return ((img_width - max_text_width) // 2, margin_y)
        elif position == Position.TOP_RIGHT:
            return (img_width - max_text_width - margin_x, margin_y)
        elif position == Position.MIDDLE_LEFT:
            return (margin_x, (img_height - text_height) // 2)
        elif position == Position.MIDDLE_CENTER:
            return ((img_width - max_text_width) // 2, (img_height - text_height) // 2)
        elif position == Position.MIDDLE_RIGHT:
            return (img_width - max_text_width - margin_x, (img_height - text_height) // 2)
        elif position == Position.BOTTOM_LEFT:
            return (margin_x, img_height - text_height - margin_y)
        elif position == Position.BOTTOM_CENTER:
            return ((img_width - max_text_width) // 2, img_height - text_height - margin_y)
        elif position == Position.BOTTOM_RIGHT:
            return (img_width - max_text_width - margin_x, img_height - text_height - margin_y)
        
    @staticmethod
    def calculate_text_position_video(position, img_width, img_height, max_text_width, total_text_height):
        """Calcula la posición del texto asegurando que no exceda los límites del video y mantenga un margen adecuado."""
        # Definir márgenes
        margin_x = int(0.1 * img_width)  # 10% del ancho de la imagen
        margin_y = int(0.05 * img_height)  # 5% del alto de la imagen

        # Posicionamiento en base a la opción seleccionada
        if position == Position.TOP_LEFT:
            return (margin_x, margin_y)
        elif position == Position.TOP_CENTER:
            return ((img_width - max_text_width) // 2, margin_y)
        elif position == Position.TOP_RIGHT:
            return (img_width - max_text_width - margin_x, margin_y)
        elif position == Position.MIDDLE_LEFT:
            return (margin_x, (img_height - total_text_height) // 2)
        elif position == Position.MIDDLE_CENTER:
            return ((img_width - max_text_width) // 2, (img_height - total_text_height) // 2)
        elif position == Position.MIDDLE_RIGHT:
            return (img_width - max_text_width - margin_x, (img_height - total_text_height) // 2)
        elif position == Position.BOTTOM_LEFT:
            return (margin_x, img_height - total_text_height - margin_y)
        elif position == Position.BOTTOM_CENTER:
            return ((img_width - max_text_width) // 2, img_height - total_text_height - margin_y)
        elif position == Position.BOTTOM_RIGHT:
            return (img_width - max_text_width - margin_x, img_height - total_text_height - margin_y)
    @staticmethod
    def split_subtitles(subtitle_text, font, max_width):
        """Split long subtitles into shorter lines for better readability."""
        wrapped_lines = []
        current_line = ""
        for word in subtitle_text.split():
            test_line = f"{current_line} {word}".strip()
            # Calculate the width using textlength
            line_width = font.getlength(test_line)
            if line_width <= max_width:  # Adjust to fit within the width
                current_line = test_line
            else:
                wrapped_lines.append(current_line)
                current_line = word
        if current_line:
            wrapped_lines.append(current_line)
        return '\n'.join(wrapped_lines)

    @staticmethod
    def generate_subtitle(txt, video_size, 
                        position=Position.MIDDLE_CENTER,
                        style=Style.BOLD,
                        bg_color=None):
        """
        Generate subtitles with customizable styles and positioning.
        """
        # Obtener parámetros del estilo utilizando StyleHelper
        style_params = SubtitleHelper.get_style_parameters(style)
        
        # Asignar los valores obtenidos del estilo
        font_path = style_params['font_path']
        max_fontsize = style_params['fontsize']
        stroke_color = style_params['stroke_color']
        stroke_width = style_params['stroke_width']
        text_color = style_params['text_color']
        
        # Cargar la fuente con el tamaño máximo        font = ImageFont.truetype(font_path, max_fontsize)
        max_text_width = video_size[0] * 0.95  # Permitimos un padding (95% del ancho del video)

        # Dividir los subtítulos largos en líneas más cortas para que se ajusten al ancho del video
        txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)

        # Create a temporary image to measure text
        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)

        # Reducir dinámicamente el tamaño de la fuente en un 5% hasta que el texto quepa dentro del límite
        bbox = temp_draw.multiline_textbbox((0, 0), txt, font=font)
        while (bbox[2] - bbox[0]) > max_text_width and max_fontsize > 50:
            max_fontsize = int(max_fontsize * 0.95)  # Reducir el tamaño de la fuente en un 5%
            font = ImageFont.truetype(font_path, max_fontsize)
            txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)  # Volver a dividir el texto
            bbox = temp_draw.multiline_textbbox((0, 0), txt, font=font)

        # Calcular el tamaño del texto basado en las líneas divididas
        bbox = temp_draw.multiline_textbbox((0, 0), txt, font=font)
        text_width = bbox[2] - bbox[0]  # right - left
        text_height = bbox[3] - bbox[1]  # bottom - top

        # Generar el clip de texto con el nuevo tamaño de fuente
        text_clip = TextClip(
            txt,
            font=font_path,
            fontsize=max_fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            size=(max_text_width, None),  # Limitar el ancho
            align='center',
            method='caption'
        )

        # Calcular la posición del texto basada en el valor del enum `Position`
        final_position = SubtitleHelper.calculate_text_position_video(
            position, 
            video_size[0], video_size[1], 
            text_width, 
            text_height
        )

        # Si se especifica un color de fondo, añadir una caja de fondo
        if bg_color:
            padding_x = 20
            padding_y = 10
            box_width = text_width + 2 * padding_x
            box_height = text_height + 2 * padding_y

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
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip


    @staticmethod
    def add_subtitles(video, subtitle_file, style=Style.DEFAULT, position=Position.MIDDLE_CENTER):
        """Add subtitles to the video based on the provided subtitle file."""
        try:
            subtitles = SubtitlesClip(subtitle_file, lambda txt: SubtitleHelper.generate_subtitle(txt, video.size, style=style, position=position))
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(f"❌ Error adding subtitles: {e}")
        
    @staticmethod
    def get_style_parameters(style: Style):
        """
        Returns the style parameters (font, size, colors, stroke) for different styles.
        The styles cover both 'thumbnail' and 'subtitle' use cases.
        """
        styles = {
            # Estilos para subtítulos
            Style.DEFAULT: {
                'font_path': "C:\\Windows\\Fonts\\Helvetica.ttf",
                'fontsize': 90,
                'stroke_color': 'black',
                'stroke_width': 3,
                'text_color': 'white',
                'bg_color': None
            },
            Style.BOLD: {
                'font_path': "Resources\\Fonts\\sub.otf",
                'fontsize': 100,
                'stroke_color': 'white',
                'stroke_width': 5,
                'text_color': 'yellow',
                'bg_color': 'black'
            },
            Style.MINIMAL: {
                'font_path': "C:\\Windows\\Fonts\\Arial.ttf",
                'fontsize': 80,
                'stroke_color': 'black',
                'stroke_width': 0,
                'text_color': 'white',
                'bg_color': None
            },
            Style.ELEGANT: {
                'font_path': "C:\\Windows\\Fonts\\Times.ttf",
                'fontsize': 95,
                'stroke_color': 'gray',
                'stroke_width': 2,
                'text_color': 'white',
                'bg_color': 'navy'
            },
            Style.VIBRANT: {
                'font_path': "Resources\\Fonts\\sub.otf",
                'fontsize': 115,
                'stroke_color': 'blue',
                'stroke_width': 6,
                'text_color': 'red',
                'bg_color': 'yellow'
            },
            Style.CASUAL: {
                'font_path': "C:\\Windows\\Fonts\\ComicSansMS.ttf",
                'fontsize': 85,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'orange',
                'bg_color': None
            },
            Style.SUBTLE: {
                'font_path': "Resources\\Fonts\\sub.otf",
                'fontsize': 70,
                'stroke_color': 'green',
                'stroke_width': 2,
                'text_color': 'green',
                'bg_color': 'black'
            },
            Style.FORMAL: {
                'font_path': "C:\\Windows\\Fonts\\Georgia.ttf",
                'fontsize': 100,
                'stroke_color': 'darkblue',
                'stroke_width': 6,
                'text_color': 'white',
                'bg_color': 'white'
            },
            Style.DRAMATIC: {
                'font_path': "Resources\\Fonts\\Arial.otf",
                'fontsize': 120,
                'stroke_color': 'black',
                'stroke_width': 6,
                'text_color': 'yellow',
                'bg_color': None
            },
            
            # Estilos para portadas (thumbnail)
            Style.THUMBNAIL_BOLD: {
                'font_path': "Resources\\Fonts\\title.otf",
                'fontsize': 120,
                'stroke_color': 'red',
                'stroke_width': 8,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_MINIMAL: {
                'font_path': "Resources\\Fonts\\Intensa.ttf",
                'fontsize': 100,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_INTENSA: {
                'font_path': "Resources\\Fonts\\Intensa.ttf",
                'fontsize': 100,
                'stroke_color': 'red',
                'stroke_width': 8,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_ELEGANT: {
                'font_path': "C:\\Windows\\Fonts\\Times.ttf",
                'fontsize': 150,
                'stroke_color': 'gray',
                'stroke_width': 2,
                'text_color': 'white',
                'bg_color': 'darkblue'
            },
            Style.THUMBNAIL_VIBRANT: {
                'font_path': "Resources\\Fonts\\title.otf",
                'fontsize': 115,
                'stroke_color': 'blue',
                'stroke_width': 6,
                'text_color': 'red',
                'bg_color': 'yellow'
            },
            Style.THUMBNAIL_CASUAL: {
                'font_path': "Resources\\Fonts\\Cartoon.ttf",
                'fontsize': 180,
                'stroke_color': 'white',
                'stroke_width': 8,
                'text_color': 'red',
                'bg_color': None
            },
            Style.THUMBNAIL_CARTOON: {
                'font_path': "Resources\\Fonts\\Cartoon.ttf",
                'fontsize': 180,
                'stroke_color': 'white',
                'stroke_width': 8,
                'text_color': 'red',
                'bg_color': None
            }
        }
        # Return the style parameters for the given style
        return styles.get(style, styles[Style.DEFAULT])  # Fallback to DEFAULT if style is not found