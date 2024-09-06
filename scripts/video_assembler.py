from pydub import AudioSegment
import moviepy.editor as mp
from moviepy.editor import vfx
from moviepy.video.fx import resize, crop
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import TextClip,CompositeVideoClip, ImageClip
from moviepy.editor import *
import configparser
import os
import textwrap
from colorama import init, Fore
from PIL import Image, ImageDraw
import numpy as np
from enum import Enum

# Initialize colorama
init(autoreset=True)

class Position(Enum):
    TOP = 'top'
    MIDDLE = 'middle'
    BOTTOM = 'bottom'

class Style(Enum):
    DEFAULT = 'default'
    BOLD = 'bold'
    MINIMAL = 'minimal'

class VideoAssembler:
    def __init__(self, media_files, subtitle_file, voiceover_file, output_file):
        self.media_files = media_files
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.settings = self.load_settings()
        self.aspect_ratio = self.settings.get('aspect_ratio', '9:16')
        self.background_music = self.settings.get('background_music', '')

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read('settings.config')
        return config['VideoResult']
    
    def get_target_dimensions(self):
        if self.aspect_ratio == '9:16':
            return 1080, 1920  # Vertical
        elif self.aspect_ratio == '16:9':
            return 1920, 1080  # Horizontal
        else:
            raise ValueError(Fore.RED + "Invalid aspect ratio value in settings. Use '9:16' or '16:9'.")

    def adjust_aspect_ratio(self, video_clip):
        # Get target dimensions based on aspect ratio from config file
        target_w, target_h = self.get_target_dimensions()

        # Calculate aspect ratios
        video_aspect_ratio = video_clip.w / video_clip.h
        target_aspect_ratio = target_w / target_h

        if video_aspect_ratio > target_aspect_ratio:
            # Video is wider than target, scale by height and crop width
            video_clip_resized = resize.resize(video_clip, height=target_h)
        else:
            # Video is taller than target, scale by width and crop height
            video_clip_resized = resize.resize(video_clip, width=target_w)

        # Crop the video to match the target dimensions
        video_clip_cropped = crop.crop(video_clip_resized, width=target_w, height=target_h, x_center=video_clip_resized.w // 2, y_center=video_clip_resized.h // 2)

        return video_clip_cropped

    def adjust_videos(self):
        if not self.media_files:
            raise ValueError(Fore.RED + "No media files provided. Please provide at least one video file.")

        adjusted_files = []
        if not os.path.exists(".temp"):
            os.makedirs(".temp")
            
        for media_file in self.media_files:
            try:
                print(Fore.CYAN + f"Processing file: {media_file}")
                clip = mp.VideoFileClip(media_file)
                
                if not clip:
                    print(Fore.RED + f"Failed to load video file: {media_file}")
                    continue
                
                adjusted_clip = self.adjust_aspect_ratio(clip)
                
                if not adjusted_clip:
                    print(Fore.RED + f"Failed to adjust aspect ratio for file: {media_file}")
                    continue
                
                adjusted_file = os.path.join(".temp", f"adjusted_{os.path.basename(media_file)}")
                print(Fore.CYAN + f"Saving adjusted file to: {adjusted_file}")
                adjusted_clip.write_videofile(adjusted_file)
                
                adjusted_files.append(adjusted_file)
                print(Fore.GREEN + f"File processed and saved: {adjusted_file}")
            
            except Exception as e:
                print(Fore.RED + f"Error processing file {media_file}: {e}")
        
        print(Fore.GREEN + f"Adjusted files: {adjusted_files}")
        return adjusted_files

    def split_subtitles(self, subtitle_text):
        # Split long subtitles into shorter lines
        return '\n'.join(textwrap.wrap(subtitle_text, width=15))  # Adjust width for 2 or 3 words per line

    def assemble_video(self):
        # Adjust the videos
        adjusted_files = self.adjust_videos()
        #adjusted_files = self.media_files
        # Verify that adjusted files are not empty
        if not adjusted_files:
            raise ValueError(Fore.RED + "No adjusted video files were created. Please check the input files and settings.")
        
        # Create a list of video clips from adjusted files
        try:
            clips = [mp.VideoFileClip(mf) for mf in adjusted_files]
        except Exception as e:
            raise ValueError(Fore.RED + f"Error loading video clips: {e}")
        
        # Verify that the list of clips is not empty
        if not clips:
            raise ValueError(Fore.RED + "No video clips could be loaded. Please check the adjusted files.")
        
        # Concatenate the video clips
        try:
            video = mp.concatenate_videoclips(clips)
        except Exception as e:
            raise ValueError(Fore.RED + f"Error concatenating video clips: {e}")
        
        # Load the voiceover file and adjust the video duration
        try:
            audio = mp.AudioFileClip(self.voiceover_file)
        except Exception as e:
            raise ValueError(Fore.RED + f"Error loading voiceover file: {e}")
        
        audio = audio.audio_fadeout(2)
        video = video.set_audio(audio)

        # Process background music if specified
        if self.background_music:
            try:
                music = AudioSegment.from_mp3(self.background_music)
                temp_music_file = os.path.join(".temp", "temp_music.wav")
                music.export(temp_music_file, format="wav")

                # Load the converted music file and mix it with the voiceover
                music_clip = mp.AudioFileClip(temp_music_file).volumex(0.2)

                music_clip = music_clip.subclip(0, audio.duration).audio_fadeout(2)
                background_audio = mp.CompositeAudioClip([audio, music_clip])
                video = video.set_audio(background_audio)
            except Exception as e:
                raise ValueError(Fore.RED + f"Error processing background music: {e}")

        # Add subtitles if specified
        if self.subtitle_file:
            try:
                subtitles = SubtitlesClip(self.subtitle_file, 
                                          lambda txt: self.generate_subtitle(txt, video.size))
                subtitles = subtitles.set_position(('center', 'center'))
                video = mp.CompositeVideoClip([video, subtitles])
            except Exception as e:
                raise ValueError(Fore.RED + f"Error adding subtitles: {e}")
        
        # Write the final video file
        try:
            video = video.subclip(0, audio.duration)
            video = video.fadeout(2)
            video.write_videofile(self.output_file, write_logfile=True)
        except Exception as e:
            print(Fore.RED + f"Error writing video file: {e}")

        print(Fore.GREEN + "Video processing completed successfully.")
    
    def generate_subtitle(self, txt, video_size, 
                      position=Position.MIDDLE,
                      style=Style.BOLD,
                      bg_color=None,
                      text_color='yellow'):
        """
        Genera subtítulos de forma simplificada.
        """
        # Asegurarse de que el texto esté en Unicode
        txt = txt.encode('utf-8').decode('utf-8')

        # Configuración de estilos internos según el estilo general seleccionado
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
            bg_color = None  # Sin fondo en estilo minimalista
        else:  # Style.DEFAULT
            font = 'Helvetica'
            fontsize = 120
            stroke_color = 'black'
            stroke_width = 3

        # Configurar el texto del subtítulo
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
        ).set_position('center', 'center')

        # Obtener el tamaño del texto
        text_width, text_height = text_clip.size
        padding_x = 20
        padding_y = 10
        box_width = text_width + 2 * padding_x
        box_height = text_height + 2 * padding_y

        # Crear el fondo solo si se especifica un color de fondo
        if bg_color:
            image = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            radius = 25  # Borde redondeado
            draw.rounded_rectangle(
                [(0, 0), (box_width, box_height)],
                radius=radius,
                fill=(0, 0, 0, int(255 * 0.6)) if bg_color == 'blue' else bg_color
            )
            image_np = np.array(image)
            image_clip = ImageClip(image_np).set_duration(text_clip.duration)
        else:
            image_clip = None

        # Posicionar el subtítulo según el parámetro 'position'
        if position == Position.TOP:
            final_position = ('center', 0.1 * video_size[1])
        elif position == Position.MIDDLE:
            final_position = ('center', 'center')
        else:  # Position.BOTTOM
            final_position = ('center', 0.8 * video_size[1])

        # Combinamos el fondo (si existe) con el texto
        if image_clip:
            subtitle_clip = CompositeVideoClip([image_clip, text_clip]).set_position(final_position)
        else:
            subtitle_clip = text_clip.set_position(final_position)

        return subtitle_clip