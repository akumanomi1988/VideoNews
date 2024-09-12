import uuid
from pathlib import Path
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from colorama import init, Fore, Style
import json
import random
# Initialize colorama
init(autoreset=True)

class TextToSpeech:
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