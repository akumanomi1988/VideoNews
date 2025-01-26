from pydub import AudioSegment

import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import TextClip, CompositeVideoClip, ImageClip, VideoFileClip
from moviepy.video.fx import resize, crop
from moviepy.video.fx import fadein, fadeout
import os
import textwrap
from colorama import init, Fore
from PIL import Image, ImageDraw
import numpy as np

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper


# Initialize colorama
init(autoreset=True)

class VideoAssembler:
    def __init__(self, subtitle_file, voiceover_file, output_file, media_videos=None, media_images=None, aspect_ratio="9:16", background_music="", transition_type="crossfade",  # Nuevo: tipo de transición
                 transition_duration=1,        # Duración de transición en segundos
                 image_effect="pan",           # Nuevo: efecto para imágenes
                 effect_direction="left"):     # Dirección del efecto):
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.media_videos = media_videos or []
        self.media_images = media_images or []
        self.aspect_ratio = aspect_ratio
        self.background_music = background_music
        self.transition_type = transition_type
        self.transition_duration = transition_duration
        self.image_effect = image_effect
        self.effect_direction = effect_direction
    def apply_image_effect(self, image_clip):
        """Aplica efectos de movimiento a las imágenes estáticas."""
        if self.image_effect == "pan":
            return self._apply_pan_effect(image_clip)
        elif self.image_effect == "zoom":
            return self._apply_zoom_effect(image_clip)
        # Añadir más efectos aquí
        return image_clip

    def _apply_pan_effect(self, clip):
        """Efecto de paneo horizontal o vertical."""
        w, h = clip.size
        target_w, target_h = self.get_target_dimensions()
        
        if self.effect_direction in ["left", "right"]:
            x_speed = (w - target_w)/clip.duration
            return clip.crop(x1=lambda t: x_speed*t if self.effect_direction == "right" else w - target_w - x_speed*t,
                            y1=0, x2=lambda t: target_w + x_speed*t, y2=target_h)
        else:  # up/down
            y_speed = (h - target_h)/clip.duration
            return clip.crop(y1=lambda t: y_speed*t if self.effect_direction == "down" else h - target_h - y_speed*t,
                            x1=0, y2=lambda t: target_h + y_speed*t, x2=target_w)

    def _apply_zoom_effect(self, clip):
        """Efecto de zoom gradual."""
        return clip.resize(lambda t: 1 + 0.2*t/clip.duration)
    def get_target_dimensions(self):
        """Return target dimensions based on the specified aspect ratio."""
        if self.aspect_ratio == '9:16':
            return 1080, 1920  # Vertical aspect ratio
        elif self.aspect_ratio == '16:9':
            return 1920, 1080  # Horizontal aspect ratio
        else:
            raise ValueError(Fore.RED + "❌ Invalid aspect ratio. Use '9:16' or '16:9'.")

    def adjust_aspect_ratio(self, clip):
        """Resize and crop the video/image clip to match the target aspect ratio."""
        target_w, target_h = self.get_target_dimensions()
        clip_aspect_ratio = clip.w / clip.h
        target_aspect_ratio = target_w / target_h

        # Resize and crop based on aspect ratio comparison
        if clip_aspect_ratio > target_aspect_ratio:
            resized_clip = resize.resize(clip, height=target_h)
        else:
            resized_clip = resize.resize(clip, width=target_w)

        cropped_clip = crop.crop(resized_clip, width=target_w, height=target_h, 
                                 x_center=resized_clip.w // 2, y_center=resized_clip.h // 2)
        return cropped_clip
    def concatenate_with_transitions(self, clips):
        """Concatena clips con transiciones personalizadas."""
        if self.transition_type == "crossfade":
            return mp.concatenate_videoclips(
                clips,
                method="compose",
                transition=self._crossfade_transition,
                transition_duration=self.transition_duration
            )
        elif self.transition_type == "slide":
            return mp.concatenate_videoclips(
                clips,
                padding=-self.transition_duration,
                method="compose"
            )
        # Añadir más tipos de transiciones aquí
        return mp.concatenate_videoclips(clips)

    def _crossfade_transition(self, clipA, clipB):
        """Transición de fundido cruzado personalizado."""
        return clipA.crossfadeout(self.transition_duration).crossfadein(self.transition_duration)
    def adjust_media(self):
        """Process and adjust media files (videos and images) to match the aspect ratio."""
        adjusted_clips = []

        # Process video files
        for media_file in self.media_videos:
            try:
                print(Fore.CYAN + f"📹 Processing video: {media_file}")
                video_clip = VideoFileClip(media_file)
                adjusted_clips.append(self.adjust_aspect_ratio(video_clip))
            except Exception as e:
                print(Fore.RED + f"❌ Error processing video {media_file}: {e}")

        # Process image files
        audio_duration = mp.AudioFileClip(self.voiceover_file).duration
        for image_file in self.media_images:
            try:
                print(Fore.CYAN + f"🖼️ Processing image: {image_file}")
                image_clip = ImageClip(image_file, duration=audio_duration / len(self.media_images))
                image_clip = self.adjust_aspect_ratio(image_clip)
                image_clip = self.apply_image_effect(image_clip)  # Aplicar efecto
                adjusted_clips.append(image_clip)
                # image_clip = ImageClip(image_file, duration=audio_duration / len(self.media_images))
                # image_clip.fps = 24
                # adjusted_clips.append(self.adjust_aspect_ratio(image_clip))
            except Exception as e:
                print(Fore.RED + f"❌ Error processing image {image_file}: {e}")

        return adjusted_clips

    def _slide_transition(self, clipA, clipB):
        """Transición de deslizamiento lateral."""
        return clipB.set_position(lambda t: (min(t/self.transition_duration, 1) * clipA.w, 0))

    def add_transition(clip1, clip2, transition_duration=1):
        """
        Agrega una transición de fundido entre dos clips.
        """
        clip1 = clip1.crossfadeout(transition_duration)
        clip2 = clip2.crossfadein(transition_duration)

        return mp.concatenate_videoclips([clip1, clip2], padding=-transition_duration)
    def split_subtitles(self, subtitle_text):
        """Split long subtitles into shorter lines for better readability."""
        return '\n'.join(textwrap.wrap(subtitle_text, width=15))

    def assemble_video(self,style:Style = Style.DEFAULT,position: Position = Position.MIDDLE_CENTER):
        """Assemble and create the final video with subtitles, voiceover, and optional background music."""
        adjusted_clips = self.adjust_media()

        if not adjusted_clips:
            raise ValueError(Fore.RED + "🚨 No media files could be adjusted. Check your inputs.")

        try:
            # video = mp.concatenate_videoclips(adjusted_clips)
            video = self.concatenate_with_transitions(adjusted_clips)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error concatenating video clips: {e}")

        try:
            audio = mp.AudioFileClip(self.voiceover_file).audio_fadeout(2)
            video = video.set_audio(audio)
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error loading voiceover: {e}")

        # Agregar música de fondo si se proporciona
        if self.background_music:
            try:
                music = mp.AudioFileClip(self.background_music)
                background_audio = mp.CompositeAudioClip([audio, music.volumex(0.2)])
                video = video.set_audio(background_audio)

            except Exception as e:
                raise ValueError(Fore.RED + f"❌ Error processing background music: {e}")

        if self.subtitle_file:
            try:
                subtitles = SubtitlesClip(
                self.subtitle_file, 
                lambda txt: self.generate_subtitle(txt, video.size, style=style, position=position)
            )
                subtitles = (
                subtitles.set_duration(video.duration)
                .set_fps(video.fps)
                .precompute()  # Pre-renderizado
            )
                final_position = SubtitleHelper.calculate_text_position_video(
                position=position,
                img_width=video.size[0],
                img_height=video.size[1],
                max_text_width=0.95 * video.size[0],
                total_text_height=video.size[1]/3
            )
                
                subtitles = subtitles.set_position(final_position)

                video = CompositeVideoClip([video, subtitles])
                # # Position the subtitle according to the 'position' parameter
                # final_position = SubtitleHelper.calculate_text_position_video(position=position,img_width=video.size[0],img_height=video.size[1],max_text_width=0.95 * video.size[0],total_text_height=video.size[1]/3)
                
                # subtitles = SubtitlesClip(self.subtitle_file, lambda txt: self.generate_subtitle(txt, video.size,style=style,position=position))
                # subtitles = subtitles.set_position(final_position)
                # video = CompositeVideoClip([video, subtitles])
            except Exception as e:
                raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")

        # Escribir el archivo de video final
        try:
            video = video.subclip(0, audio.duration).fadeout(2)
            video.write_videofile(
                self.output_file,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='slow',
                ffmpeg_params=['-crf', '22']
            )
            print(Fore.GREEN + "✅ Video processing completed successfully.")
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error writing final video: {e}")
        
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
    
# Parte principal para instanciar y ejecutar la clase
if __name__ == "__main__":
    # Definir los parámetros usando archivos de la carpeta .temp
    ImageHelper.enhance_thumbnail(".temp/NONE_6ffe59f0-6917-48ca-aae1-d960230c69a2.png", 
                                  "El increible titular está guapísimo para esta noticia impresionante", 
                                  Position.BOTTOM_CENTER, Style.THUMBNAIL_BOLD, 2000, 95)
    subtitle_file = "scripts/.temp/subtitles.srt"  # Archivo de subtítulos
    voiceover_file = ".temp/c6f3db91-5d9a-4db5-8d33-4a22039bb973.mp3"  # Archivo de voz en off
    output_file = ".temp/Análisis_de_los_Siete_Estados_C2.mp4"  # Archivo de salida
    media_images = [
        ".temp/NONE_8f38d792-7e26-4eac-9e39-3476fb47ed30.png",
        ".temp/NONE_af2e1d86-dffb-4ebe-a193-8aca7d2c51bc.png",
        ".temp/NONE_058309ef-7531-4093-971c-d65578544e3e.png",
        ".temp/NONE_2a737ae5-7d13-4835-8cb2-cc318a0f2445.png"
        # Agregar más imágenes según sea necesario
    ]
    media_videos = []  # Lista de videos adicionales, si tienes alguno para incluir
    background_music = "Resources\Music\SweetBananaMelody.mp3"  # Ruta a la música de fondo, si deseas agregar una

    # Crear instancia de VideoAssembler
    video_assembler = VideoAssembler(
        subtitle_file=subtitle_file,
        voiceover_file=voiceover_file,
        output_file=output_file,
        media_images=media_images,
        media_videos=media_videos,
        background_music=background_music,
        aspect_ratio="16:9"
    )
    video_assembler.assemble_video(style=Style.BOLD,position=Position.BOTTOM_CENTER)

