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
            font = ImageFont.truetype(font_path, round(font_size))

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
                font = ImageFont.truetype(font_path, round(font_size))

            # Dibujar cada línea de texto en la imagen, sin superponerlas
            for line in lines:
                # Calcular el ancho de cada línea para centrarla
                line_width, _ = draw.textsize(line, font=font)
                centered_x = text_position[0] + (max_text_width - line_width) // 2

                if stroke_width > 0:
                    draw.text((centered_x, text_position[1]), line, fill=text_color, 
                            stroke_fill=stroke_color, stroke_width=stroke_width, font=font, align='center')
                else:
                    draw.text((centered_x, text_position[1]), line, fill=text_color, font=font, align='center')
                
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
        """Calcula posición con márgenes dinámicos y asegura máximo 25% de altura"""
        # Margen vertical del 5% de la altura del video
        margin_y = img_height * 0.05
        max_height = img_height * 0.25  # Máximo 25% de la altura

        # Ajustar altura si supera el máximo
        total_text_height = min(total_text_height, max_height)

        positions = {
            Position.TOP_LEFT: (0.05 * img_width, margin_y),
            Position.TOP_CENTER: ('center', margin_y),
            Position.TOP_RIGHT: (0.95 * img_width - max_text_width, margin_y),
            Position.MIDDLE_LEFT: (0.05 * img_width, (img_height - total_text_height)/2),
            Position.MIDDLE_CENTER: ('center', (img_height - total_text_height)/2),
            Position.MIDDLE_RIGHT: (0.95 * img_width - max_text_width, (img_height - total_text_height)/2),
            Position.BOTTOM_LEFT: (0.05 * img_width, img_height - total_text_height - margin_y),
            Position.BOTTOM_CENTER: ('center', img_height - total_text_height - margin_y),
            Position.BOTTOM_RIGHT: (0.95 * img_width - max_text_width, img_height - total_text_height - margin_y)
        }
        
        return positions.get(position, ('center', 'center'))

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
    def generate_subtitle(self, txt, video_size, position=Position.BOTTOM_CENTER, style=Style.DEFAULT):
        """Genera subtítulos con fondo semitransparente y texto responsive"""
        # Configuración de estilo
        style_params = SubtitleHelper.get_style_parameters(style)
        
        # Parámetros dinámicos basados en resolución
        base_fontsize = int(min(video_size) * 0.045)  # 4.5% del lado más pequeño
        max_width = video_size[0] * 0.9  # 90% del ancho del video
        max_height = video_size[1] * 0.25  # Máximo 25% de altura
        
        # Crear texto con wrappers dinámicos
        wrapper = textwrap.TextWrapper(width=int(max_width / (base_fontsize * 0.6)), break_long_words=False)
        wrapped_text = '\n'.join(wrapper.wrap(txt))
        
        # Crear clip de texto
        text_clip = TextClip(
            wrapped_text,
            font=style_params['font_path'],
            fontsize=base_fontsize,
            color=style_params['text_color'],
            stroke_color=style_params['stroke_color'],
            stroke_width=style_params['stroke_width'],
            align='center',
            method='pango',  # Mejor manejo de texto multilínea
            size=(max_width, None)
        )
        
        # Ajustar tamaño automáticamente
        text_clip = text_clip.resize(lambda t: min(1 + t * 0.005, 1.1))  # Efecto de escala suave
        
        # Crear fondo semitransparente
        bg_color = style_params.get('bg_color', (0, 0, 0, 178))  # Negro semitransparente por defecto
        if not isinstance(bg_color, tuple):
            bg_color = (0, 0, 0, 178)  # Fallback a negro semitransparente
            
        # Crear fondo con borde redondeado
        text_size = text_clip.size
        padding = base_fontsize * 0.5
        background = (
            ImageClip(np.zeros((int(text_size[1] + padding*2), int(text_size[0] + padding*2), 4), dtype=np.uint8))
            .set_opacity(bg_color[3]/255)
            .set_duration(text_clip.duration)
        )
        
        # Combinar elementos
        subtitle = CompositeVideoClip([
            background.set_position(('center', 'center')),
            text_clip.set_position(('center', 'center'))
        ])
        
        # Posicionamiento final
        final_position = SubtitleHelper.calculate_text_position_video(
            position=position,
            img_width=video_size[0],
            img_height=video_size[1],
            max_text_width=max_width,
            total_text_height=text_size[1] + padding*2
        )
        
        return subtitle.set_position(final_position)

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
        Devuelve parámetros de estilo mejorados con:
        - Fuentes relativas a proyecto (no absolutas)
        - Tamaños responsive (% de altura de video)
        - Fondos semitransparentes (RGBA)
        - Stroke proporcional al tamaño
        """
        base_config = {
            "font_dir": "fonts/",  # Directorio relativo para fuentes
            "base_size_ratio": 0.1,  # 4% de la altura del video
            "thumbnail_size_ratio": 0.2  # 6% para thumbnails
        }

        styles = {
            # ESTILOS PARA SUBTÍTULOS -----------------------------------------------
            Style.DEFAULT: {
                'font': "Roboto-Medium.ttf",
                'text_color': '#FFFFFF',
                'stroke_color': '#000000',
                'stroke_width': 1.5,
                'bg_color': (0, 0, 0, 178),  # Negro 70% opacidad
                'fontsize_ratio': 1.0,
                'max_lines': 3
            },
            
            Style.BOLD: {
                'font': "Impact.ttf",
                'text_color': '#FFD700',
                'stroke_color': '#000000',
                'stroke_width': 3.0,
                'bg_color': (0, 0, 0, 200),
                'fontsize_ratio': 1.1,
                'max_lines': 2
            },
            
            Style.MINIMAL: {
                'font': "Roboto-Light.ttf",
                'text_color': '#FFFFFF',
                'stroke_color': None,
                'stroke_width': 0,
                'bg_color': (255, 255, 255, 50),
                'fontsize_ratio': 0.9,
                'max_lines': 3
            },
            
            Style.ELEGANT: {
                'font': "PlayfairDisplay-Regular.ttf",
                'text_color': '#E6E6FA',
                'stroke_color': '#2A2A2A',
                'stroke_width': 1.2,
                'bg_color': (25, 25, 112, 150),  # Azul noche
                'fontsize_ratio': 1.05,
                'max_lines': 2
            },
            
            Style.VIBRANT: {
                'font': "BebasNeue-Regular.ttf",
                'text_color': '#FFFF00',
                'stroke_color': '#9400D3',
                'stroke_width': 2.5,
                'bg_color': (75, 0, 130, 160),  # Índigo
                'fontsize_ratio': 1.2,
                'max_lines': 2
            },
            
            Style.CASUAL: {
                'font': "Quicksand-Medium.ttf",
                'text_color': '#FFA500',
                'stroke_color': None,
                'stroke_width': 0,
                'bg_color': (255, 255, 255, 30),
                'fontsize_ratio': 0.95,
                'max_lines': 3
            },
            
            Style.SUBTLE: {
                'font': "OpenSans-Regular.ttf",
                'text_color': '#90EE90',
                'stroke_color': '#006400',
                'stroke_width': 1.0,
                'bg_color': (0, 0, 0, 100),
                'fontsize_ratio': 0.85,
                'max_lines': 3
            },
            
            Style.FORMAL: {
                'font': "TimesNewRoman.ttf",
                'text_color': '#FFFFFF',
                'stroke_color': '#00008B',
                'stroke_width': 2.0,
                'bg_color': (25, 25, 112, 180),
                'fontsize_ratio': 1.0,
                'max_lines': 2
            },
            
            Style.DRAMATIC: {
                'font': "AlfaSlabOne-Regular.ttf",
                'text_color': '#FF0000',
                'stroke_color': '#000000',
                'stroke_width': 4.0,
                'bg_color': (0, 0, 0, 220),
                'fontsize_ratio': 1.3,
                'max_lines': 2
            },
            
            # ESTILOS PARA THUMBNAILS -----------------------------------------------
            Style.THUMBNAIL_BOLD: {
                'font': "title.otf",
                'text_color': '#FFFFFF',
                'stroke_color': '#FF0000',
                'stroke_width': 4.0,
                'bg_color': (0, 0, 0, 150),
                'fontsize_ratio': 1.5,
                'max_lines': 2
            },
            
            Style.THUMBNAIL_MINIMAL: {
                'font': "Raleway-ExtraLight.ttf",
                'text_color': '#FFFFFF',
                'stroke_color': None,
                'stroke_width': 0,
                'bg_color': (255, 255, 255, 30),
                'fontsize_ratio': 1.8,
                'max_lines': 1
            },
            
            Style.THUMBNAIL_ELEGANT: {
                'font': "GreatVibes-Regular.ttf",
                'text_color': '#FFFFFF',
                'stroke_color': '#000000',
                'stroke_width': 1.5,
                'bg_color': (139, 0, 0, 160),  # Rojo oscuro
                'fontsize_ratio': 2.0,
                'max_lines': 1
            },
            
            Style.THUMBNAIL_VIBRANT: {
                'font': "Lobster-Regular.ttf",
                'text_color': '#FF0000',
                'stroke_color': '#FFFF00',
                'stroke_width': 3.0,
                'bg_color': (0, 0, 255, 140),
                'fontsize_ratio': 1.7,
                'max_lines': 2
            },
            
            Style.THUMBNAIL_CASUAL: {
                'font': "Pacifico-Regular.ttf",
                'text_color': '#FF69B4',
                'stroke_color': '#FFFFFF',
                'stroke_width': 2.0,
                'bg_color': (255, 255, 255, 50),
                'fontsize_ratio': 1.6,
                'max_lines': 2
            }
        }

        # Merge config base + estilo específico
        style_params = {**base_config, **styles.get(style, styles[Style.DEFAULT])}
        
        # Resolver path completo de la fuente
        style_params['font_path'] = os.path.join(
            style_params['font_dir'], 
            style_params['font']
        )
        
        # Calcular tamaño de fuente responsive
        is_thumbnail = "THUMBNAIL" in style.name
        size_ratio = style_params['thumbnail_size_ratio'] if is_thumbnail else style_params['base_size_ratio']
        style_params['fontsize'] = size_ratio * style_params['fontsize_ratio']
        
        return style_params