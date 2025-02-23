import uuid
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import json
import random
import os
import edge_tts
import asyncio
import tempfile
from pathlib import Path
from colorama import init, Fore, Style
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import uuid
import os
from pathlib import Path
from colorama import Fore
import os
from pathlib import Path
from uuid import uuid4
from pydub import AudioSegment
from colorama import Fore
from bark import generate_audio, preload_models, SAMPLE_RATE
import re
# Initialize colorama
init(autoreset=True)

class TTSEdge:
    def __init__(self, api_key: str = None, output_dir="output_audio"):
        """
        Initializes the TtsHuggingFace object with the directory where the audio files will be saved.
        
        :param api_key: Optional API key for authentication (not used in this context).
        :param output_dir: Directory where the audio files will be saved.
        """
        # Set output directory, creating it if it doesn't exist
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def text_to_speech(self, text: str, voice: str = "es-ES-XimenaNeural - es-ES (Female)", rate: int = 0, pitch: int = 0):
        """
        Converts the text to speech using edge_tts and saves the result as an MP3 file.
        
        :param text: The text content to convert to speech.
        :param voice: The voice to use for the TTS conversion.
        :param rate: Speech rate adjustment percentage (-100 to 100).
        :param pitch: Pitch adjustment in Hz (-20 to 20).
        :return: A tuple containing the path of the file where the audio is saved and any error message.
        """
        try:
            if not text.strip():
                return None, "Input text is empty."

            if not voice:
                return None, "No voice selected."

            # Prepare rate and pitch adjustments
            rate_str = f"{rate:+d}%"
            pitch_str = f"{pitch:+d}Hz"

            # Generate TTS audio using edge_tts
            communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_path = tmp_file.name
                await communicate.save(tmp_path)

            # Move the file to the output directory with a unique name
            file_name = f"{uuid.uuid4()}.mp3"
            output_path = Path(self.output_dir) / file_name
            os.rename(tmp_path, output_path)

            return str(output_path)
            
        except Exception as e:
            return None, str(e)

    async def get_voices(self) -> dict:
        """
        Get available voices using edge_tts.
        
        :return: A dictionary of voice names mapped to their short names.
        """
        voices = await edge_tts.list_voices()
        return {f"{v['ShortName']} - {v['Locale']} ({v['Gender']})": v['ShortName'] for v in voices}

    
    def text_to_speech_file(self, text: str, language: str = 'es', voice: str = 'es-ES-XimenaNeural - es-ES (Female)') -> str:
        """
        Generate TTS audio and return the path of the saved audio file.

        :param text: The text to convert to speech.
        :param language: The language for the voice (e.g., 'es' for Spanish).
        :param voice: The preferred voice for the TTS conversion.
        :return: The path of the audio file.
        """
        voices_dict = asyncio.run(self.get_voices())

        # Print available voices before filtering
        # print(Fore.CYAN + "Available voices:")
        # for name, short_name in voices_dict.items():
        #     print(Fore.BLUE + f"- {name} (Short Name: {short_name})")

        # Filter voices to get only those in the requested language
        filtered_voices = {name: short_name for name, short_name in voices_dict.items() if language in name}
        for name, short_name in filtered_voices.items():
            print(Fore.BLUE + f"- {name} (Short Name: {short_name})")
        # Handle voice selection
        if not filtered_voices:
            raise Exception(Fore.RED + "No voices available for the selected language.")

        # Check if the preferred voice exists in the filtered voices
        if voice in filtered_voices:
            selected_voice = voice.split(" - ")[0]  # Get the short name of the voice
            print(Fore.GREEN + f"Using preferred voice: {voice}")
        else:
            # Choose a random voice from the filtered voices
            selected_voice = random.choice(list(filtered_voices.values()))
            print(Fore.YELLOW + f"Preferred voice not found. Using random voice: {selected_voice}")

        # Call the asynchronous function to generate audio
        audio_file = asyncio.run(self.text_to_speech(text, selected_voice))

        return audio_file

class TTSElevenlabs:
    def __init__(self, credentials_path, quota_min:int):
        self.credentials_path = Path(credentials_path)
        self.quota_min = quota_min
        self.api_key, self.model_id, self.voice_id = self.get_valid_account()
        
        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)
        else:
            raise ValueError("No se encontró una cuenta válida con suficiente cuota.")

    def text_to_speech_file(self, text: str, output_dir: str) -> str:
        """
        Converts the text to speech and saves the result as an MP3 file.

        :param text: The text content to convert to speech.
        :param output_dir: The directory where the audio file will be saved.
        :return: The path of the file where the audio is saved.
        """
        # Call to the text-to-speech API with detailed parameters
        response = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id=self.model_id,
            voice_settings=VoiceSettings(
                stability=0.5,  # Reduce la estabilidad para hacer que la voz sea más dinámica
                similarity_boost=0.8,  # Reduce un poco la similitud para agregar un toque más humano
                style=0.8,  # Incrementa el estilo para que la voz tenga más énfasis, lo que la hace sonar más agresiva
                use_speaker_boost=True,  # Mantén el uso del speaker boost para darle más fuerza a la voz
                speed_boost=1.7  # Incrementa la velocidad de la voz para que suene más rápida, similar a algunos videos virales
            ),
        )

        # Create a unique file name for the output MP3 file
        file_name = f"{uuid.uuid4()}.mp3"

        # Create the full file path using pathlib
        output_path = Path(output_dir) / file_name

        # Write the audio stream to the file
        with open(output_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        # Print a success message with color
        print(Fore.GREEN + f"A new audio file was saved successfully at {output_path}")

        # Return the path of the saved audio file
        return str(output_path)
            
    def get_valid_account(self):
        with open(self.credentials_path, 'r') as f:
            accounts = json.load(f)
        
        valid_accounts = []
        for account_name, account_data in accounts.items():
            api_key = account_data['ApiKey']
            client = ElevenLabs(api_key=api_key)
            
            try:
                user = client.user.get()
                subscription = user.subscription
                remaining_characters = subscription.character_limit - subscription.character_count
                
                if remaining_characters >= self.quota_min:
                    print(Fore.GREEN + f"Cuenta {account_name} tiene {remaining_characters} caracteres restantes.")
                    valid_accounts.append((api_key, account_data))
                else:
                    print(Fore.YELLOW + f"Cuenta {account_name} no tiene suficiente cuota ({remaining_characters} caracteres).")
            except Exception as e:
                print(Fore.RED + f"Error al verificar la cuenta {account_name}: {str(e)}")
        
        if not valid_accounts:
            return None, None, None
        
        # Seleccionar una cuenta aleatoria de las válidas
        selected_api_key, selected_account = random.choice(valid_accounts)
        
        # Seleccionar una voz aleatoria de la cuenta seleccionada
        selected_voice = random.choice(selected_account['Voices'])
        
        print(Fore.GREEN + f"Usando cuenta con API Key: {selected_api_key[:10]}... y voz ID: {selected_voice['ID']}")
        
        return selected_api_key, "eleven_multilingual_v2", selected_voice['ID']
import os
from pathlib import Path
from uuid import uuid4
from scipy.io.wavfile import write as write_wav
from colorama import Fore
from bark import generate_audio, preload_models, SAMPLE_RATE

class TTSBark:
    def __init__(self, output_dir="output_audio", optimize_for_low_vram=False):
        """
        Inicializa el objeto TTSBark con el directorio donde se guardarán los archivos de audio.
        
        :param output_dir: Directorio donde se guardarán los archivos de audio.
        :param optimize_for_low_vram: Si es True, activa optimizaciones para sistemas con VRAM limitada.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        if optimize_for_low_vram:
            print(Fore.YELLOW + "Optimizing Bark for low VRAM usage...")
            os.environ["SUNO_OFFLOAD_CPU"] = "True"
            os.environ["SUNO_USE_SMALL_MODELS"] = "True"
        
        preload_models()

    def _split_text_into_segments(self, text: str, max_length=100) -> list:
        """
        Divide el texto de entrada en segmentos basados en límites de oraciones y longitud máxima.
        
        :param text: Texto a dividir.
        :param max_length: Longitud máxima de cada segmento (en caracteres).
        :return: Lista de segmentos de texto.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            candidate = f"{current_segment} {sentence}".strip() if current_segment else sentence
            if len(candidate) <= max_length:
                current_segment = candidate
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence
        if current_segment:
            segments.append(current_segment.strip())
        return segments

    def _combine_audio_segments(self, audio_segments: list) -> AudioSegment:
        """
        Combina múltiples objetos AudioSegment en uno solo.
        
        :param audio_segments: Lista de AudioSegment.
        :return: AudioSegment combinado.
        """
        combined = AudioSegment.empty()
        for segment in audio_segments:
            combined += segment
        return combined

    def text_to_speech_file(self, text: str, language: str = 'es', voice: str = 'v2/es_speaker_3') -> str:
        """
        Genera audio TTS usando Bark y retorna la ruta del archivo de audio generado.
        
        :param text: Texto a convertir en audio.
        :param language: Idioma para la voz (por ejemplo, 'es' para inglés).
        :param voice: Voz preferida para la conversión TTS.
        :return: Ruta del archivo de audio.
        """
        try:
            if not text.strip():
                raise ValueError("Input text is empty.")
            if not voice:
                raise ValueError("No voice selected.")
            
            segments = self._split_text_into_segments(text)
            print(Fore.CYAN + f"Text split into {len(segments)} segments.")
            
            audio_segments = []
            for i, segment in enumerate(segments):
                audio_array = generate_audio(segment, history_prompt=voice)
                # Convertir el array de audio a un objeto AudioSegment sin escribir en disco.
                audio_segment = AudioSegment(
                    data=audio_array.tobytes(),
                    sample_width=audio_array.dtype.itemsize,
                    frame_rate=SAMPLE_RATE,
                    channels=1
                )
                audio_segments.append(audio_segment)
                print(Fore.GREEN + f"Generated audio for segment {i+1}/{len(segments)}.")
            
            combined_audio = self._combine_audio_segments(audio_segments)
            output_file_name = f"{uuid4()}.wav"
            output_path = Path(self.output_dir) / output_file_name
            combined_audio.export(output_path, format="wav")
            
            print(Fore.GREEN + f"A new combined audio file was saved successfully at {output_path}")
            return str(output_path)
        
        except Exception as e:
            print(Fore.RED + f"Error during TTS generation: {str(e)}")
            return None
        
    def get_voices(self) -> dict:
        """
        Get all available voices in Bark.
        
        :return: A dictionary of voice names mapped to their identifiers.
        """
        # List of all available voices in Bark
        voices = {
            "English Speaker 0": "v2/en_speaker_0",
            "English Speaker 1": "v2/en_speaker_1",
            "English Speaker 2": "v2/en_speaker_2",
            "English Speaker 3": "v2/en_speaker_3",
            "English Speaker 4": "v2/en_speaker_4",
            "English Speaker 5": "v2/en_speaker_5",
            "English Speaker 6": "v2/en_speaker_6",
            "English Speaker 7": "v2/en_speaker_7",
            "English Speaker 8": "v2/en_speaker_8",
            "English Speaker 9": "v2/en_speaker_9",
            "Spanish Speaker 0": "v2/es_speaker_0",
            "Spanish Speaker 1": "v2/es_speaker_1",
            "Spanish Speaker 2": "v2/es_speaker_2",
            "Spanish Speaker 3": "v2/es_speaker_3",
            "Spanish Speaker 4": "v2/es_speaker_4",
            "Spanish Speaker 5": "v2/es_speaker_5",
            "Spanish Speaker 6": "v2/es_speaker_6",
            "Spanish Speaker 7": "v2/es_speaker_7",
            "Spanish Speaker 8": "v2/es_speaker_8",
            "Spanish Speaker 9": "v2/es_speaker_9",
            "French Speaker 0": "v2/fr_speaker_0",
            "French Speaker 1": "v2/fr_speaker_1",
            "French Speaker 2": "v2/fr_speaker_2",
            "French Speaker 3": "v2/fr_speaker_3",
            "French Speaker 4": "v2/fr_speaker_4",
            "French Speaker 5": "v2/fr_speaker_5",
            "French Speaker 6": "v2/fr_speaker_6",
            "French Speaker 7": "v2/fr_speaker_7",
            "French Speaker 8": "v2/fr_speaker_8",
            "French Speaker 9": "v2/fr_speaker_9",
            "German Speaker 0": "v2/de_speaker_0",
            "German Speaker 1": "v2/de_speaker_1",
            "German Speaker 2": "v2/de_speaker_2",
            "German Speaker 3": "v2/de_speaker_3",
            "German Speaker 4": "v2/de_speaker_4",
            "German Speaker 5": "v2/de_speaker_5",
            "German Speaker 6": "v2/de_speaker_6",
            "German Speaker 7": "v2/de_speaker_7",
            "German Speaker 8": "v2/de_speaker_8",
            "German Speaker 9": "v2/de_speaker_9",
            "Italian Speaker 0": "v2/it_speaker_0",
            "Italian Speaker 1": "v2/it_speaker_1",
            "Italian Speaker 2": "v2/it_speaker_2",
            "Italian Speaker 3": "v2/it_speaker_3",
            "Italian Speaker 4": "v2/it_speaker_4",
            "Italian Speaker 5": "v2/it_speaker_5",
            "Italian Speaker 6": "v2/it_speaker_6",
            "Italian Speaker 7": "v2/it_speaker_7",
            "Italian Speaker 8": "v2/it_speaker_8",
            "Italian Speaker 9": "v2/it_speaker_9",
            "Portuguese Speaker 0": "v2/pt_speaker_0",
            "Portuguese Speaker 1": "v2/pt_speaker_1",
            "Portuguese Speaker 2": "v2/pt_speaker_2",
            "Portuguese Speaker 3": "v2/pt_speaker_3",
            "Portuguese Speaker 4": "v2/pt_speaker_4",
            "Portuguese Speaker 5": "v2/pt_speaker_5",
            "Portuguese Speaker 6": "v2/pt_speaker_6",
            "Portuguese Speaker 7": "v2/pt_speaker_7",
            "Portuguese Speaker 8": "v2/pt_speaker_8",
            "Portuguese Speaker 9": "v2/pt_speaker_9",
            "Polish Speaker 0": "v2/pl_speaker_0",
            "Polish Speaker 1": "v2/pl_speaker_1",
            "Polish Speaker 2": "v2/pl_speaker_2",
            "Polish Speaker 3": "v2/pl_speaker_3",
            "Polish Speaker 4": "v2/pl_speaker_4",
            "Polish Speaker 5": "v2/pl_speaker_5",
            "Polish Speaker 6": "v2/pl_speaker_6",
            "Polish Speaker 7": "v2/pl_speaker_7",
            "Polish Speaker 8": "v2/pl_speaker_8",
            "Polish Speaker 9": "v2/pl_speaker_9",
            "Turkish Speaker 0": "v2/tr_speaker_0",
            "Turkish Speaker 1": "v2/tr_speaker_1",
            "Turkish Speaker 2": "v2/tr_speaker_2",
            "Turkish Speaker 3": "v2/tr_speaker_3",
            "Turkish Speaker 4": "v2/tr_speaker_4",
            "Turkish Speaker 5": "v2/tr_speaker_5",
            "Turkish Speaker 6": "v2/tr_speaker_6",
            "Turkish Speaker 7": "v2/tr_speaker_7",
            "Turkish Speaker 8": "v2/tr_speaker_8",
            "Turkish Speaker 9": "v2/tr_speaker_9",
        }
        return voices