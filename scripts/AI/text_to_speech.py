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