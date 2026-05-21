import os
from enum import Enum
from typing import Optional, Tuple, Dict, Any

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
from colorama import init, Fore
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from pydub import AudioSegment

# Inicializa colorama para salida en consola coloreada
init(autoreset=True)

# ------------------ CONSTANTES DE CONFIGURACIÓN ------------------
FONT_PATHS = {
    "helvetica": r"C:\Windows\Fonts\Helvetica.ttf",
    "arial": r"C:\Windows\Fonts\Arial.ttf",
    "times": r"C:\Windows\Fonts\Times.ttf",
    "comic": r"C:\Windows\Fonts\ComicSansMS.ttf",
    "georgia": r"C:\Windows\Fonts\Georgia.ttf",
    "sub_otf": r"Resources\Fonts\sub.otf",
    "title_otf": r"Resources\Fonts\title.otf",
    "intensa": r"Resources\Fonts\Intensa.ttf",
    "cartoon": r"Resources\Fonts\Cartoon.ttf",
    "arial_otf": r"Resources\Fonts\Arial.otf"
}
TEMP_DIR = ".temp"
TEMP_MUSIC_FILENAME = "temp_music.wav"

# ------------------ ENUMS ------------------
class Position(Enum):
    """Posiciones posibles para colocar texto en imágenes o videos."""
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
    """Estilos visuales para subtítulos y portadas."""
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
    """Utilidades para procesar videos: ajuste de aspecto, concatenación, etc."""

    @staticmethod
    def get_target_dimensions(aspect_ratio: str) -> Tuple[int, int]:
        """Devuelve dimensiones objetivo según el aspect ratio."""
        if aspect_ratio == '9:16':
            return 1080, 1920
        elif aspect_ratio == '16:9':
            return 1920, 1080
        raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

    @staticmethod
    def adjust_aspect_ratio(clip, aspect_ratio: str):
        """Redimensiona y recorta el clip para que coincida con el aspect ratio objetivo."""
        target_w, target_h = VideoHelper.get_target_dimensions(aspect_ratio)
        clip_aspect = clip.w / clip.h
        target_aspect = target_w / target_h

        if clip_aspect > target_aspect:
            resized = resize.resize(clip, height=target_h)
        else:
            resized = resize.resize(clip, width=target_w)

        return crop.crop(
            resized,
            width=target_w,
            height=target_h,
            x_center=resized.w // 2,
            y_center=resized.h // 2
        )

    @staticmethod
    def process_video(file_path: str, aspect_ratio: str):
        """Procesa un archivo de video ajustando su aspect ratio."""
        try:
            print(Fore.CYAN + f"📹 Processing video: {file_path}")
            video_clip = VideoFileClip(file_path)
            return VideoHelper.adjust_aspect_ratio(video_clip, aspect_ratio)
        except Exception as e:
            print(Fore.RED + f"❌ Error processing video {file_path}: {e}")
            return None

    @staticmethod
    def process_image(file_path: str, aspect_ratio: str, audio_duration: float, num_images: int):
        """Procesa una imagen ajustando su aspect ratio y duración."""
        try:
            print(Fore.CYAN + f"🖼️ Processing image: {file_path}")
            image_clip = ImageClip(file_path)
            adjusted_clip = VideoHelper.adjust_aspect_ratio(image_clip, aspect_ratio)
            image_duration = audio_duration / num_images
            return adjusted_clip.set_duration(image_duration)
        except Exception as e:
            print(Fore.RED + f"❌ Error processing image {file_path}: {e}")
            return None

# ------------------ AUDIO HELPER ------------------
class AudioHelper:
    """Utilidades para procesar archivos de audio: voiceover y música de fondo."""

    @staticmethod
    def get_voiceover_audio(voiceover_file: str) -> AudioFileClip:
        """Carga y retorna el audio de voiceover con fundido de salida."""
        try:
            audio = AudioFileClip(voiceover_file).audio_fadeout(2)
            return audio
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error loading voiceover: {e}")

    @staticmethod
    def add_background_music(video, music_file: str, audio_duration: float):
        """Agrega música de fondo a un video."""
        try:
            music = AudioSegment.from_mp3(music_file)
            os.makedirs(TEMP_DIR, exist_ok=True)
            temp_music_path = os.path.join(TEMP_DIR, TEMP_MUSIC_FILENAME)
            music.export(temp_music_path, format="wav")

            with AudioFileClip(temp_music_path) as music_clip:
                music_clip = (
                    music_clip
                    .volumex(0.2)
                    .subclip(0, audio_duration)
                    .audio_fadeout(2)
                )
                composite_audio = CompositeAudioClip([video.audio, music_clip])
                video = video.set_audio(composite_audio)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error processing background music: {e}")
        return video

# ------------------ IMAGE HELPER ------------------
class ImageHelper:
    """Utilidades para procesar imágenes: reducción de tamaño y mejora de miniaturas."""

    @staticmethod
    def reduce_image_size(
        image_path: str,
        max_size_kb: int,
        reduction_percentage: int
    ) -> None:
        """
        Reduce el tamaño de una imagen si excede el máximo especificado.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"{Fore.RED}❌ Image file not found: {image_path}")
        if not (1 <= reduction_percentage < 100):
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
            max_attempts = 10

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
    def enhance_thumbnail(
        image_path: str,
        text: str,
        position: Position = Position.MIDDLE_CENTER,
        style: Style = Style.THUMBNAIL_BOLD,
        max_size_kb: int = 2000,
        reduction_percentage: int = 5,
        text_size: int = 0
    ) -> None:
        """
        Mejora una miniatura agregando texto en la posición y estilo seleccionados.
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

            lines = ImageHelper._wrap_text(text, font, max_text_width, draw)
            line_heights = [draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines]
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
                draw.text(
                    (centered_x, current_y),
                    line,
                    fill=text_color,
                    stroke_fill=stroke_color if stroke_width else None,
                    stroke_width=stroke_width,
                    font=font,
                    align='center'
                )
                current_y += line_heights[idx] + line_spacing
            image.save(image_path)
            print(Fore.GREEN + f"✅ Thumbnail updated: {image_path}")
        except Exception as e:
            print(Fore.RED + f"❌ Error enhancing thumbnail: {e}")

    @staticmethod
    def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
        """Divide el texto en líneas para que no excedan el ancho máximo."""
        words = text.split()
        if not words:
            return [""]
        lines = []
        current_line = words[0]
        for word in words[1:]:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
        return lines

# ------------------ SUBTITLE HELPER ------------------
class SubtitleHelper:
    """Utilidades para generar y posicionar subtítulos en videos."""

    @staticmethod
    def calculate_text_position_image(
        position: Position,
        img_width: int,
        img_height: int,
        max_text_width: int,
        text_height: int
    ) -> Tuple[int, int]:
        """Calcula la posición del texto en una imagen con margen del 10%."""
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
        return (margin_x, margin_y)

    @staticmethod
    def calculate_text_position_video(
        position: Position,
        img_width: int,
        img_height: int,
        max_text_width: int,
        total_text_height: int
    ) -> Tuple[int, int]:
        """Calcula la posición del texto en un video con margen adecuado."""
        margin_x = int(0.1 * img_width)
        margin_y = int(0.05 * img_height)

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
        return (margin_x, margin_y)

    @staticmethod
    def split_subtitles(subtitle_text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """Divide subtítulos largos en líneas más cortas para mejor legibilidad."""
        words = subtitle_text.split()
        wrapped_lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            line_width = font.getlength(test_line)
            if line_width <= max_width:
                current_line = test_line
            else:
                wrapped_lines.append(current_line)
                current_line = word
        if current_line:
            wrapped_lines.append(current_line)
        return '\n'.join(wrapped_lines)

    @staticmethod
    def generate_subtitle(
        txt: str,
        video_size: Tuple[int, int],
        position: Position = Position.MIDDLE_CENTER,
        style: Style = Style.BOLD,
        bg_color: Optional[str] = None
    ):
        """
        Genera un clip de subtítulo con estilos y posicionamiento personalizables.
        """
        style_params = SubtitleHelper.get_style_parameters(style)
        font_path = style_params['font_path']
        max_fontsize = style_params['fontsize']
        stroke_color = style_params['stroke_color']
        stroke_width = style_params['stroke_width']
        text_color = style_params['text_color']

        font = ImageFont.truetype(font_path, max_fontsize)
        max_text_width = int(video_size[0] * 0.95)

        txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)

        temp_img = Image.new('RGB', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.multiline_textbbox((0, 0), txt, font=font)
        while (bbox[2] - bbox[0]) > max_text_width and max_fontsize > 50:
            max_fontsize = int(max_fontsize * 0.95)
            font = ImageFont.truetype(font_path, max_fontsize)
            txt = SubtitleHelper.split_subtitles(txt, font, max_text_width)
            bbox = temp_draw.multiline_textbbox((0, 0), txt, font=font)

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_clip = TextClip(
            txt,
            font=font_path,
            fontsize=max_fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            size=(max_text_width, None),
            align='center',
            method='caption'
        )

        final_position = SubtitleHelper.calculate_text_position_video(
            position,
            video_size[0], video_size[1],
            text_width,
            text_height
        )

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
    def add_subtitles(
        video,
        subtitle_file: str,
        style: Style = Style.DEFAULT,
        position: Position = Position.MIDDLE_CENTER
    ):
        """Agrega subtítulos al video usando el archivo proporcionado."""
        try:
            subtitles = SubtitlesClip(
                subtitle_file,
                lambda txt: SubtitleHelper.generate_subtitle(
                    txt, video.size, style=style, position=position
                )
            )
            return CompositeVideoClip([video, subtitles])
        except Exception as e:
            raise ValueError(f"❌ Error adding subtitles: {e}")

    @staticmethod
    def get_style_parameters(style: Style) -> Dict[str, Any]:
        """
        Devuelve los parámetros de estilo (fuente, tamaño, colores, trazo) para diferentes estilos.
        """
        styles = {
            Style.DEFAULT: {
                'font_path': FONT_PATHS["helvetica"],
                'fontsize': 90,
                'stroke_color': 'black',
                'stroke_width': 3,
                'text_color': 'white',
                'bg_color': None
            },
            Style.BOLD: {
                'font_path': FONT_PATHS["sub_otf"],
                'fontsize': 100,
                'stroke_color': 'white',
                'stroke_width': 5,
                'text_color': 'yellow',
                'bg_color': 'black'
            },
            Style.MINIMAL: {
                'font_path': FONT_PATHS["arial"],
                'fontsize': 80,
                'stroke_color': 'black',
                'stroke_width': 0,
                'text_color': 'white',
                'bg_color': None
            },
            Style.ELEGANT: {
                'font_path': FONT_PATHS["times"],
                'fontsize': 95,
                'stroke_color': 'gray',
                'stroke_width': 2,
                'text_color': 'white',
                'bg_color': 'navy'
            },
            Style.VIBRANT: {
                'font_path': FONT_PATHS["sub_otf"],
                'fontsize': 115,
                'stroke_color': 'blue',
                'stroke_width': 6,
                'text_color': 'red',
                'bg_color': 'yellow'
            },
            Style.CASUAL: {
                'font_path': FONT_PATHS["comic"],
                'fontsize': 85,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'orange',
                'bg_color': None
            },
            Style.SUBTLE: {
                'font_path': FONT_PATHS["sub_otf"],
                'fontsize': 70,
                'stroke_color': 'green',
                'stroke_width': 2,
                'text_color': 'green',
                'bg_color': 'black'
            },
            Style.FORMAL: {
                'font_path': FONT_PATHS["georgia"],
                'fontsize': 100,
                'stroke_color': 'darkblue',
                'stroke_width': 6,
                'text_color': 'white',
                'bg_color': 'white'
            },
            Style.DRAMATIC: {
                'font_path': FONT_PATHS["arial_otf"],
                'fontsize': 120,
                'stroke_color': 'black',
                'stroke_width': 6,
                'text_color': 'yellow',
                'bg_color': None
            },
            Style.THUMBNAIL_BOLD: {
                'font_path': FONT_PATHS["title_otf"],
                'fontsize': 120,
                'stroke_color': 'red',
                'stroke_width': 8,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_MINIMAL: {
                'font_path': FONT_PATHS["intensa"],
                'fontsize': 100,
                'stroke_color': None,
                'stroke_width': 0,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_INTENSA: {
                'font_path': FONT_PATHS["intensa"],
                'fontsize': 100,
                'stroke_color': 'red',
                'stroke_width': 8,
                'text_color': 'white',
                'bg_color': None
            },
            Style.THUMBNAIL_ELEGANT: {
                'font_path': FONT_PATHS["times"],
                'fontsize': 150,
                'stroke_color': 'gray',
                'stroke_width': 2,
                'text_color': 'white',
                'bg_color': 'darkblue'
            },
            Style.THUMBNAIL_VIBRANT: {
                'font_path': FONT_PATHS["title_otf"],
                'fontsize': 115,
                'stroke_color': 'blue',
                'stroke_width': 6,
                'text_color': 'red',
                'bg_color': 'yellow'
            },
            Style.THUMBNAIL_CASUAL: {
                'font_path': FONT_PATHS["cartoon"],
                'fontsize': 180,
                'stroke_color': 'white',
                'stroke_width': 8,
                'text_color': 'red',
                'bg_color': None
            },
            Style.THUMBNAIL_CARTOON: {
                'font_path': FONT_PATHS["cartoon"],
                'fontsize': 180,
                'stroke_color': 'white',
                'stroke_width': 8,
                'text_color': 'red',
                'bg_color': None
            }
        }
        return styles.get(style, styles[Style.DEFAULT])