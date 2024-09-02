import os
import pyttsx3
import configparser
from moviepy.editor import AudioFileClip
import whisper
import re
from colorama import Fore, Style, init

# Inicializar Colorama
init(autoreset=True)

class SubtitleAndVoiceGenerator:
    def __init__(self, config_file='settings.config'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.engine = pyttsx3.init()
        self.whisper_model = whisper.load_model("small")  # Load the Whisper model

        # Text-to-speech engine configuration
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id)
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1.0)

        # Set up the temporary directory in the project's root directory
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.temp')
        self.temp_dir = os.path.abspath(self.temp_dir)  # Ensure an absolute path is obtained
        os.makedirs(self.temp_dir, exist_ok=True)

    def generate_voiceover(self, text: str):
        """
        Generates a voice file (mp3) from the text using pyttsx3.
        """
        voiceover_path = os.path.join(self.temp_dir, "voiceover.mp3")
        print(f"{Fore.GREEN}Voiceover path: {voiceover_path}")

        # Using pyttsx3 to generate the audio file
        self.engine.save_to_file(text, voiceover_path)
        self.engine.runAndWait()

        self.debug_audio_file_path(voiceover_path)
        return voiceover_path

    def get_audio_duration(self, audio_file):
        """
        Gets the duration of the audio file in seconds.
        """
        # Use AudioFileClip to open the audio file
        with AudioFileClip(audio_file) as audio:
            return audio.duration

    def transcribe_audio(self, audio_file):
        """
        Uses Whisper to transcribe the audio file and obtain subtitle timings.
        """
        self.debug_audio_file_path(audio_file)
        
        try:
            # Optional parameters: language, task, temperature
            result = self.whisper_model.transcribe(
                audio_file,
                language="es",         # Specify the language if known
                temperature=0.5
            )

            return result.get('segments', [])
    
        except Exception as e:
            print(f"{Fore.RED}Error during transcription: {e}")
            return {'segments': []}

    def generate_subtitles(self, audio_file):
        """
        Generates a subtitle file (.srt) based on the audio transcription.
        """
        print(f"{Fore.CYAN}Generating subtitles for audio: {audio_file}")
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

        print(f"{Fore.GREEN}Subtitles saved to {subtitle_path}")
        return subtitle_path

    def seconds_to_hms(self, seconds):
        """
        Converts seconds into hours, minutes, and seconds.
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}", f"{m:02}", f"{s:02}"

    def debug_audio_file_path(self, audio_file):
        print(f"{Fore.YELLOW}Checking for file existence: {audio_file}")
        self.check_file_access(audio_file)
        if os.path.isfile(audio_file):
            print(f"{Fore.GREEN}The file exists.")
        else:
            print(f"{Fore.RED}Error: The file is not found at the specified path.")
            print(f"{Fore.RED}Absolute file path: {os.path.abspath(audio_file)}")

    def check_file_access(self, file_path):
        if os.path.isfile(file_path):
            print(f"{Fore.GREEN}File found: {file_path}")
            try:
                with open(file_path, 'rb') as f:
                    print(f"{Fore.GREEN}File access verified.")
            except IOError as e:
                print(f"{Fore.RED}Error accessing the file: {e}")
        else:
            print(f"{Fore.RED}The file does not exist at the path: {file_path}")
