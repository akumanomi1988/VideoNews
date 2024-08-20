import pyttsx3
import os
import configparser
from gtts import gTTS
from moviepy.editor import AudioFileClip
import whisper
import json

class SubtitleAndVoiceGenerator:
    def __init__(self, text, config_file='settings.config'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.text = text
        self.engine = pyttsx3.init()
        self.whisper_model = whisper.load_model("base")  # Cargar el modelo Whisper

        # Configuración del motor de texto a voz
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id)
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

        self.temp_dir = ".temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def generate_voiceover(self):
        """
        Genera un archivo de voz (mp3) a partir del texto usando pyttsx3 o gTTS.
        """
        voiceover_path = os.path.join(self.temp_dir, "voiceover.mp3")
        print(f"Generating voiceover for: {self.text}")
        print(f"Voiceover path: {voiceover_path}")

        # Usando pyttsx3 para generar el archivo de audio
        self.engine.save_to_file(self.text, voiceover_path)
        self.engine.runAndWait()

        return voiceover_path

    def get_audio_duration(self, audio_file):
        """
        Obtiene la duración del archivo de audio en segundos.
        """
        with AudioFileClip(audio_file) as audio:
            return audio.duration

    def transcribe_audio(self, audio_file):
        """
        Usa Whisper para transcribir el archivo de audio y obtener los tiempos de subtítulos.
        """
        result = self.whisper_model.transcribe(audio_file)
        return result['segments']

    def generate_subtitles(self, audio_file):
        """
        Genera un archivo de subtítulos (.srt) basado en la transcripción del audio.
        """
        print(f"Generating subtitles for audio: {audio_file}")
        subtitle_path = os.path.join(self.temp_dir, "subtitles.srt")
        segments = self.transcribe_audio(audio_file)
        
        with open(subtitle_path, 'w') as file:
            for i, segment in enumerate(segments):
                start_time = segment['start']
                end_time = segment['end']
                text = segment['text']
                
                start_h, start_m, start_s = self.seconds_to_hms(start_time)
                end_h, end_m, end_s = self.seconds_to_hms(end_time)
                
                file.write(f"{i + 1}\n")
                file.write(f"{start_h}:{start_m}:{start_s},000 --> {end_h}:{end_m}:{end_s},000\n")
                file.write(f"{text}\n\n")

        return subtitle_path

    def seconds_to_hms(self, seconds):
        """
        Convierte segundos en horas, minutos y segundos.
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}", f"{m:02}", f"{s:02}"

