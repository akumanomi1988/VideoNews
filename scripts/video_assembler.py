from pydub import AudioSegment

import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import TextClip, CompositeVideoClip, ImageClip, VideoFileClip
from moviepy.video.fx import resize, crop

import os
import textwrap
from colorama import init, Fore
from PIL import Image, ImageDraw
import numpy as np

from scripts.helpers.media_helper import ImageHelper, Position, Style, SubtitleHelper


# Initialize colorama
init(autoreset=True)

class VideoAssembler:
    def __init__(self, subtitle_file, voiceover_file, output_file, media_videos=None, media_images=None, aspect_ratio="9:16", background_music=""):
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.media_videos = media_videos or []
        self.media_images = media_images or []
        self.aspect_ratio = aspect_ratio
        self.background_music = background_music
    
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
                image_clip.fps = 24
                adjusted_clips.append(self.adjust_aspect_ratio(image_clip))
            except Exception as e:
                print(Fore.RED + f"❌ Error processing image {image_file}: {e}")

        return adjusted_clips

    def split_subtitles(self, subtitle_text):
        """Split long subtitles into shorter lines for better readability."""
        return '\n'.join(textwrap.wrap(subtitle_text, width=15))

    def assemble_video(self,style:Style = Style.DEFAULT,position: Position = Position.MIDDLE_CENTER):
        """Assemble and create the final video with subtitles, voiceover, and optional background music."""
        adjusted_clips = self.adjust_media()

        if not adjusted_clips:
            raise ValueError(Fore.RED + "🚨 No media files could be adjusted. Check your inputs.")

        try:
            video = mp.concatenate_videoclips(adjusted_clips)
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
                # Position the subtitle according to the 'position' parameter
                final_position = SubtitleHelper.calculate_text_position_video(position=position,img_width=video.size[0],img_height=video.size[1],max_text_width=0.8 * video.size[0],total_text_height=video.size[1]/3)
                
                subtitles = SubtitlesClip(self.subtitle_file, lambda txt: self.generate_subtitle(txt, video.size,style=style,position=position))
                subtitles = subtitles.set_position(final_position)
                video = CompositeVideoClip([video, subtitles])
            except Exception as e:
                raise ValueError(Fore.RED + f"❌ Error adding subtitles: {e}")

        # Escribir el archivo de video final
        try:
            video = video.subclip(0, audio.duration).fadeout(2)
            video.write_videofile(self.output_file, write_logfile=True)
            print(Fore.GREEN + "✅ Video processing completed successfully.")
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error writing final video: {e}")

    def generate_subtitle(self, txt, video_size, 
                      position=Position.MIDDLE_CENTER,
                      style=Style.BOLD,
                      bg_color=None,
                      text_color='yellow'):
        """
        Generate subtitles in a simplified way.
        """
        # Ensure the text is in Unicode
        txt = txt.encode('utf-8').decode('utf-8')

        # Internal style configuration based on the selected general style
        style_params = SubtitleHelper.get_style_parameters(style)
        
        # Asignar los valores obtenidos del estilo
        font = style_params['font_path']
        fontsize = style_params['fontsize']
        stroke_color = style_params['stroke_color']
        stroke_width = style_params['stroke_width']
        text_color = style_params['text_color']
        bg_color = style_params['bg_color']
   
        # Configure the subtitle text with 'caption' method
        text_clip = TextClip(
            txt,
            font=font,
            fontsize=fontsize,
            color=text_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(video_size[0]*0.9, None),
            align='center'
        )

        # Get the size of the text
        text_width, text_height = text_clip.size
        padding_x = 20
        padding_y = 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y


        # Limit the height of the text
        max_height = video_size[1] / 3
        if text_height > max_height:
            scale_factor = max_height / text_height
            text_clip = text_clip.resize(newsize=(int(text_width * scale_factor), int(max_height)))
            box_width = int(text_width * scale_factor) + 2 * padding_x
            box_height = int(max_height) + 2 * padding_y
        # Create the background only if a background color is specified
        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25  # Rounded corners
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=(0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)
        else:
            image_clip = None
        
        # final_position = SubtitleHelper.calculate_text_position_image(position=position,img_width=video_size[1],img_height=video_size[2],max_text_width=0.8 * video_size[2],total_text_height=max_height)
        final_position = SubtitleHelper.calculate_text_position_video(position=position,img_width=video_size[0],img_height=video_size[1],max_text_width=0.8 * video_size[0],total_text_height=max_height)
        # Position the subtitle according to the 'position' parameter
        # if position == Position.TOP_CENTER:
        #     final_position = ('center', 0.1 * video_size[1])
        # elif position == Position.MIDDLE_CENTER:
        #     final_position = ('center', 'center')
        # else:  # Position.BOTTOM_CENTER
        #     final_position = ('center', 0.8 * video_size[1])

        # Combine the background (if it exists) with the text
        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip
    
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

