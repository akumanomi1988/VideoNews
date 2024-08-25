from pydub import AudioSegment
import moviepy.editor as mp
from moviepy.editor import vfx
from moviepy.video.fx import resize, crop
from moviepy.video.tools.subtitles import SubtitlesClip
import configparser
import os
import textwrap

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
            raise ValueError("Invalid aspect ratio value in settings. Use '9:16' or '16:9'.")
            
    def adjust_aspect_ratio(self, video_clip):
        # Obtener las dimensiones objetivo según la relación de aspecto del archivo de configuración
        target_w, target_h = self.get_target_dimensions()

        # Calcular la relación de aspecto del video y la deseada
        video_aspect_ratio = video_clip.w / video_clip.h
        target_aspect_ratio = target_w / target_h

        if video_aspect_ratio > target_aspect_ratio:
            # El video es más ancho que el objetivo, escalar por altura y recortar ancho
            video_clip_resized = resize.resize(video_clip, height=target_h)
        else:
            # El video es más alto que el objetivo, escalar por ancho y recortar altura
            video_clip_resized = resize.resize(video_clip, width=target_w)

        # Recortar el video para que se ajuste al tamaño objetivo
        video_clip_cropped = crop.crop(video_clip_resized, width=target_w, height=target_h, x_center=video_clip_resized.w // 2, y_center=video_clip_resized.h // 2)

        return video_clip_cropped


    def adjust_videos(self):
        if not self.media_files:
            raise ValueError("No media files provided. Please provide at least one video file.")

        adjusted_files = []
        if not os.path.exists(".temp"):
            os.makedirs(".temp")
            
        for media_file in self.media_files:
            try:
                print(f"Processing file: {media_file}")
                clip = mp.VideoFileClip(media_file)
                
                if not clip:
                    print(f"Failed to load video file: {media_file}")
                    continue
                
                adjusted_clip = self.adjust_aspect_ratio(clip)
                
                if not adjusted_clip:
                    print(f"Failed to adjust aspect ratio for file: {media_file}")
                    continue
                
                adjusted_file = os.path.join(".temp", f"adjusted_{os.path.basename(media_file)}")
                print(f"Saving adjusted file to: {adjusted_file}")
                adjusted_clip.write_videofile(adjusted_file)
                
                adjusted_files.append(adjusted_file)
                print(f"File processed and saved: {adjusted_file}")
            
            except Exception as e:
                print(f"Error processing file {media_file}: {e}")
        
        print(f"Adjusted files: {adjusted_files}")
        return adjusted_files

    def split_subtitles(self, subtitle_text):
        # Divide subtítulos largos en líneas más cortas
        return '\n'.join(textwrap.wrap(subtitle_text, width=15))  # Ajusta el ancho a 2 o 3 palabras por línea

    def assemble_video(self):
        # Ajustar los videos
        adjusted_files = self.adjust_videos()
        
        # Verificar que los archivos ajustados no estén vacíos
        if not adjusted_files:
            raise ValueError("No adjusted video files were created. Please check the input files and settings.")
        
        # Crear la lista de clips de video a partir de los archivos ajustados
        try:
            clips = [mp.VideoFileClip(mf) for mf in adjusted_files]
        except Exception as e:
            raise ValueError(f"Error loading video clips: {e}")
        
        # Verificar que la lista de clips no esté vacía
        if not clips:
            raise ValueError("No video clips could be loaded. Please check the adjusted files.")
        
        # Concatenar los clips de video
        try:
            video = mp.concatenate_videoclips(clips)
        except Exception as e:
            raise ValueError(f"Error concatenating video clips: {e}")
        
        # Cargar el archivo de voz en off y ajustar la duración del video
        try:
            audio = mp.AudioFileClip(self.voiceover_file)
        except Exception as e:
            raise ValueError(f"Error loading voiceover file: {e}")
        
        video_duration = audio.duration
        video = video.set_audio(audio).set_duration(video_duration)

        # Convertir la música de fondo si se especifica
        if self.background_music:
            try:
                music = AudioSegment.from_mp3(self.background_music)
                temp_music_file = os.path.join(".temp", "temp_music.wav")
                music.export(temp_music_file, format="wav")

                # Cargar el archivo de música convertido y combinarlo con la voz en off
                music_clip = mp.AudioFileClip(temp_music_file).volumex(0.2)
                background_audio = mp.CompositeAudioClip([audio, music_clip])
                video = video.set_audio(background_audio)
            except Exception as e:
                raise ValueError(f"Error processing background music: {e}")

        # Añadir subtítulos si se especifican
        if self.subtitle_file:
            try:
                subtitles = SubtitlesClip(self.subtitle_file, 
                                        lambda txt: self.generate_subtitle(txt, video.size))
                subtitles = subtitles.set_position(('center', 'center')).set_duration(video_duration)
                video = mp.CompositeVideoClip([video, subtitles])
            except Exception as e:
                raise ValueError(f"Error adding subtitles: {e}")
        
        # Escribir el video final en el archivo
        try:
            video.write_videofile(self.output_file,write_logfile=True)#, codec="libx264", audio_codec="aac")
        except Exception as e:
            print(f"Error writing video file: {e}")

        print("Video processing completed successfully.")


    def generate_subtitle(self, txt, video_size):
            return mp.TextClip(self.split_subtitles(txt), 
                            font='Arial', 
                            fontsize=40, 
                            color='white',
                            size=video_size, 
                            method='label')