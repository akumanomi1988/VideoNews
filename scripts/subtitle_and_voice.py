import pyttsx3
import os
import configparser
from moviepy.editor import AudioFileClip  # Usa la clase correcta para manejar archivos de audio
import whisper
import re

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

        # Configurar el directorio temporal en el directorio raíz del proyecto
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.temp')
        self.temp_dir = os.path.abspath(self.temp_dir)  # Asegúrate de obtener una ruta absoluta
        os.makedirs(self.temp_dir, exist_ok=True)

    def generate_voiceover(self):
        """
        Genera un archivo de voz (mp3) a partir del texto usando pyttsx3.
        """
        voiceover_path = os.path.join(self.temp_dir, "voiceover.mp3")
        print(f"Generating voiceover for: {self.text}")
        print(f"Voiceover path: {voiceover_path}")

        # Usando pyttsx3 para generar el archivo de audio
        self.engine.save_to_file(self.text, voiceover_path)
        self.engine.runAndWait()

        self.debug_audio_file_path(voiceover_path)
        print(voiceover_path)
        return voiceover_path

    def get_audio_duration(self, audio_file):
        """
        Obtiene la duración del archivo de audio en segundos.
        """
        # Usa AudioFileClip para abrir el archivo de audio
        with AudioFileClip(audio_file) as audio:
            return audio.duration

    def transcribe_audio(self, audio_file):
        """
        Usa Whisper para transcribir el archivo de audio y obtener los tiempos de subtítulos.
        """
        self.debug_audio_file_path(audio_file)
        
        try:
            # Parámetros opcionales: language, task, temperature
            result = self.whisper_model.transcribe(
                audio_file,
                language="es",         # Especifica el idioma si es conocido
                temperature=0.5,        # Ajusta la temperatura si es necesario
                verbose = True
            )

            return result.get('segments', [])
    
        except Exception as e:
            print(f"Error durante la transcripción: {e}")
            return {'segments': []}

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
                text = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s.,;:!?¿¡\'"-]', '', segment['text'])
                
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

    def debug_audio_file_path(self,audio_file):
        print(f"Verificando la existencia del archivo: {audio_file}")
        self.check_file_access(audio_file)
        if os.path.isfile(audio_file):
            print("El archivo existe.")
        else:
            print("Error: El archivo no se encuentra en la ruta especificada.")
            # Imprimir la ruta absoluta para verificar
            print("Ruta absoluta del archivo:", os.path.abspath(audio_file))


    def check_file_access(audio_file,file_path):
        if os.path.isfile(file_path):
            print(f"Archivo encontrado: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    print("Acceso al archivo verificado.")
            except IOError as e:
                print(f"Error al acceder al archivo: {e}")
        else:
            print(f"El archivo no existe en la ruta: {file_path}")
