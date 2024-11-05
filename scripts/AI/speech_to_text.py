import os

import pyttsx3
import configparser
from moviepy.editor import AudioFileClip
import whisper
import re
from colorama import Fore, Style, init
import time

# Inicializar Colorama
init(autoreset=True)

class stt_whisper:
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

    def transcribe_audio(self, audio_file, language="es", temperature=0.5, verbose=False, beam_size=5, best_of=3):
        """
        Uses Whisper to transcribe the audio file and obtain subtitle timings.

        Parameters:
            audio_file (str): Path to the audio file.
            language (str): Language of the audio (default is "es" for Spanish).
            temperature (float): Temperature for transcription (default is 0.5 for balanced creativity/accuracy).
            verbose (bool): If True, prints detailed transcription progress (default is False).
            beam_size (int, optional): Beam size for beam search (higher values may improve accuracy).
            best_of (int, optional): Number of alternative transcriptions to consider (improves robustness).

        Returns:
            list: A list of transcription segments with timing data.
        """
        self.debug_audio_file_path(audio_file)  # Verifies the audio file path exists and is correct
        
        print(f"{Fore.CYAN}Starting transcription for: {audio_file}")
        print(f"Language: {language}, Temperature: {temperature}, Beam Size: {beam_size}, Best Of: {best_of}")
        
        start_time = time.time()
        
        try:
            # Whisper transcription options
            options = {
                'language': language,
                'temperature': temperature
            }

            # Add optional parameters if provided
            if beam_size is not None:
                options['beam_size'] = beam_size
            if best_of is not None:
                options['best_of'] = best_of

            # Transcribe the audio file with Whisper
            result = self.whisper_model.transcribe(audio_file, **options)

            if verbose:
                print(f"{Fore.GREEN}Transcription result: {result}")

            segments = result.get('segments', [])
            
            if not segments:
                print(f"{Fore.YELLOW}No segments were returned by the transcription model.")
            
            # Report how long the transcription took
            end_time = time.time()
            print(f"{Fore.GREEN}Transcription completed in {end_time - start_time:.2f} seconds.")
            
            return segments

        except FileNotFoundError:
            print(f"{Fore.RED}Error: The audio file '{audio_file}' was not found.")
            return []

        except Exception as e:
            print(f"{Fore.RED}Error during transcription: {str(e)}")
            
            # Optionally, log the error to a file for further analysis
            # log_error(f"Transcription error: {str(e)}")
            return []
    
    # def generate_subtitles(self, audio_file):
    #     """
    #     Generates a subtitle file (.srt) based on the audio transcription.
    #     """
    #     print(f"{Fore.CYAN}Generating subtitles for audio: {audio_file}")
    #     subtitle_path = os.path.join(self.temp_dir, "subtitles.srt")
    #     segments = self.transcribe_audio(audio_file)
        
    #     with open(subtitle_path, 'w') as file:
    #         for i, segment in enumerate(segments):
    #             start_time = segment['start']
    #             end_time = segment['end']
    #             text = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s.,;:!?¿¡\'"-]', '', segment['text'])
             
    #             file.write(f"{i + 1}\n")
    #             file.write(f"{self.milis_to_hms(start_time)} --> {self.milis_to_hms(end_time)}\n")
    #             file.write(f"{text}\n\n")

    #     print(f"{Fore.GREEN}Subtitles saved to {subtitle_path}")
    #     return subtitle_path
    
    def generate_sentences_subtitles(self, audio_file):
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
    
    def generate_word_level_subtitles(self, audio_file):
        """
        Generates a subtitle file (.srt) with each word synchronized precisely with the audio.
        """
        print(f"{Fore.CYAN}Generating word-level subtitles for audio: {audio_file}")
        subtitle_path = os.path.join(self.temp_dir, "word_level_subtitles.srt")
        segments = self.transcribe_audio(audio_file)

        with open(subtitle_path, 'w') as file:
            subtitle_index = 1

            # Set minimum word duration (in milliseconds)
            min_word_duration_ms = 300  # Minimum time for a word to display
            for segment in segments:
                text = segment['text']
                start_time = segment['start']
                end_time = segment['end']
                duration_ms = (end_time - start_time) * 1000  # Segment duration in milliseconds
                words = re.findall(r'\S+', text)

                # Calculate total character length including spaces
                total_chars = sum(len(word) for word in words) + text.count(' ')

                if total_chars == 0:
                    continue

                # Start time in milliseconds
                current_time = start_time * 1000  

                for i, word in enumerate(words):
                    word_clean = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s.,;:!?¿¡\'"-]', '', word)

                    # Calculate the word duration proportional to the length of the word
                    proportional_duration_ms = max((len(word) / total_chars) * duration_ms, min_word_duration_ms)

                    # Calculate start and end time for the word
                    start_time_for_word = current_time
                    end_time_for_word = start_time_for_word + proportional_duration_ms

                    # Write the subtitle line in SRT format
                    file.write(f"{subtitle_index}\n")
                    file.write(f"{self.milis_to_hms(start_time_for_word)} --> {self.milis_to_hms(end_time_for_word)}\n")
                    file.write(f"{word_clean}\n\n")

                    # Increment the subtitle index
                    subtitle_index += 1

                    # Update current time for the next word
                    current_time = end_time_for_word

                    # Add pause duration if punctuation (increase space for better readability)
                    if i < len(words) - 1 and text[text.index(word) + len(word)] in [',', '.']:
                        current_time += proportional_duration_ms * 0.5  # Small pause after punctuation

        print(f"{Fore.GREEN}Word-level subtitles saved to {subtitle_path}")
        return subtitle_path

    def milis_to_hms(self, milis):
        seconds = milis / 1000  # Convert milliseconds to seconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        milliseconds = int(milis % 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

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

    def seconds_to_hms(self, seconds):
        """
        Convierte segundos en horas, minutos y segundos.
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}", f"{m:02}", f"{s:02}"