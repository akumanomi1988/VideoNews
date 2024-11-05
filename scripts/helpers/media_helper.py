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
    def enhance_thumbnail(image_path: str, text: str, 
                      position: Position = Position.MIDDLE_CENTER, 
                      style: Style = Style.THUMBNAIL_BOLD, 
                      max_size_kb: int = 2000, 
                      reduction_percentage: int = 5, 
                      text_size: int = 0):
        """Enhances a thumbnail by adding text in the selected position and style."""
        try:
            # Reduce image size
            ImageHelper.reduce_image_size(image_path, max_size_kb, reduction_percentage)

            # Open the image and draw text
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)

            # Obtener parámetros del estilo utilizando StyleHelper
            style_params = SubtitleHelper.get_style_parameters(style)

            # Asignar los valores obtenidos del estilo
            font_path = style_params['font_path']
            if text_size == 0:
                font_size = style_params['fontsize']
            else:
                font_size = text_size
            stroke_color = style_params['stroke_color']
            stroke_width = style_params['stroke_width']
            text_color = style_params['text_color']

            # Cargar la fuente según el estilo
            font = ImageFont.truetype(font_path, font_size)

            img_width, img_height = image.size
            max_text_width = img_width * 0.6  # Permitimos que el texto ocupe hasta el 80% del ancho

            # Dividir el texto en múltiples líneas si es necesario
            lines, current_line = [], ""
            for word in text.split():
                test_line = f"{current_line} {word}".strip()
                # Calcular el ancho del texto en esta fuente
                line_width = draw.textsize(test_line, font=font)[0]
                if line_width <= max_text_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Calcular la altura total del texto basado en las líneas divididas
            total_text_height = sum([draw.textsize(line, font=font)[1] for line in lines])

            # Calcular la posición inicial para dibujar el texto, usando el centro del texto
            text_position = SubtitleHelper.calculate_text_position_image(
                position, img_width, img_height, max_text_width, total_text_height
            )

            # Controlar el tamaño del texto en relación con el ancho de la imagen
            if text_size > 0:
                font_size = int(font_size * (text_size / 100))
                font = ImageFont.truetype(font_path, font_size)

            # Dibujar cada línea de texto en la imagen, sin superponerlas
            for line in lines:
                if stroke_width > 0:
                    draw.text(text_position, line, fill=text_color, 
                            stroke_fill=stroke_color, stroke_width=stroke_width, font=font)
                else:
                    draw.text(text_position, line, fill=text_color, font=font)
                # Moverse hacia abajo para la siguiente línea de texto
                text_position = (text_position[0], text_position[1] + font.size)

            # Sobrescribir la imagen original
            image.save(image_path)  # Guardar la imagen con el texto agregado
            print(Fore.GREEN + f"✅ Thumbnail updated: {image_path}")

        except Exception as e:
            print(Fore.RED + f"❌ Error enhancing thumbnail: {e}")

# ------------------ SUBTITLE HELPER ------------------
class SubtitleHelper:
    @staticmethod
    def calculate_text_position_image(position, img_width, img_height, max_text_width, total_text_height):
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
    @staticmethod
    def calculate_text_position_video(position, img_width, img_height, max_text_width, total_text_height):
        """Calculate text position based on enum."""
        if position == Position.TOP_LEFT:
            return ('center', 0.1 * img_height)
        elif position == Position.TOP_CENTER:
            return ('center', 0.1 * img_height)
        elif position == Position.TOP_RIGHT:
            return ('center', 0.1 * img_height)
        elif position == Position.MIDDLE_LEFT:
            return ('center', 'center')
        elif position == Position.MIDDLE_CENTER:
            return ('center', 'center')
        elif position == Position.MIDDLE_RIGHT:
            return ('center', 'center')
        elif position == Position.BOTTOM_LEFT:
            return ('center', 0.8 * img_height)
        elif position == Position.BOTTOM_CENTER:
            return ('center', 0.8 * img_height)
        elif position == Position.BOTTOM_RIGHT:
            return ('center', 0.8 * img_height)
    @staticmethod
    def split_subtitles(subtitle_text, font, max_width):
        """Split long subtitles into shorter lines for better readability."""
        wrapped_lines = []
        current_line = ""
        for word in subtitle_text.split():
            test_line = f"{current_line} {word}".strip()
            if font.getsize(test_line)[0] <= max_width:  # Adjust to fit within the width
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
        
        # Cargar la fuente con el tamaño máximo
        font = ImageFont.truetype(font_path, max_fontsize)
        max_text_width = video_size[0] * 0.8  # Permitimos un padding (80% del ancho del video)

        # Dividir los subtítulos largos en líneas más cortas para que se ajusten al ancho del video
        txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)

        # Reducir dinámicamente el tamaño de la fuente en un 5% hasta que el texto quepa dentro del límite
        while font.getsize_multiline(txt)[0] > max_text_width and max_fontsize > 50:
            max_fontsize = int(max_fontsize * 0.95)  # Reducir el tamaño de la fuente en un 5%
            font = ImageFont.truetype(font_path, max_fontsize)
            txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)  # Volver a dividir el texto

        # Calcular el tamaño del texto basado en las líneas divididas
        text_width, text_height = font.getsize_multiline(txt)

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
                'text_color': 'white'
            },
            Style.BOLD: {
                'font_path': "Fonts\\sub.otf",
                'fontsize': 100,
                'stroke_color': 'black',
                'stroke_width': 5,
                'text_color': 'yellow'
            },
            Style.MINIMAL: {
                'font_path': "C:\\Windows\\Fonts\\Arial.ttf",
                'fontsize': 80,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'white'
            },
            Style.SUBTLE: {
                'font_path': "Fonts\\sub.otf",
                'fontsize': 100,
                'stroke_color': 'green',
                'stroke_width': 5,
                'text_color': 'lightgray'
            },
            Style.FORMAL: {
                'font_path': "C:\\Windows\\Fonts\\Georgia.ttf",
                'fontsize': 85,
                'stroke_color': 'darkblue',
                'stroke_width': 4,
                'text_color': 'white'
            },
            Style.DRAMATIC: {
                'font_path': "Fonts\\dramatic.otf",
                'fontsize': 120,
                'stroke_color': 'black',
                'stroke_width': 6,
                'text_color': 'red'
            },
            # Estilos para portadas (thumbnail)
            Style.THUMBNAIL_BOLD: {
                'font_path': "Fonts\\title.otf",
                'fontsize': 120,
                'stroke_color': 'red',
                'stroke_width': 8,
                'text_color': 'white'
            },
            Style.THUMBNAIL_MINIMAL: {
                'font_path': "C:\\Windows\\Fonts\\Arial.ttf",
                'fontsize': 80,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'white'
            },
            Style.THUMBNAIL_ELEGANT: {
                'font_path': "C:\\Windows\\Fonts\\Times.ttf",
                'fontsize': 150,
                'stroke_color': 'gray',
                'stroke_width': 2,
                'text_color': 'white'
            },
            Style.THUMBNAIL_VIBRANT: {
                'font_path': "Fonts\\vibrant.otf",
                'fontsize': 115,
                'stroke_color': 'blue',
                'stroke_width': 6,
                'text_color': 'red'
            },
            Style.THUMBNAIL_CASUAL: {
                'font_path': "C:\\Windows\\Fonts\\ComicSansMS.ttf",
                'fontsize': 140,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'orange'
            }
        }

        # Return the style parameters for the given style
        return styles.get(style, styles[Style.DEFAULT])  # Fallback to DEFAULT if style is not found