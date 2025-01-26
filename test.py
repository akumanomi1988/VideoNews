from huggingface_hub import InferenceClient
import os
import random
from time import sleep
import uuid
from colorama import Fore, init
from enum import Enum
# Initialize colorama
init(autoreset=True)

class MusicGenerationStyle(Enum):
    NONE = ""
    POP = "A catchy and upbeat pop song with strong synths and vocal melodies."
    EDM = "An energetic electronic dance music track with heavy bass and drops."
    ROCK = "A dynamic rock song with electric guitars, drums, and a powerful vocal performance."
    JAZZ = "A smooth jazz track featuring improvisational solos and a relaxed rhythm."
    CLASSICAL = "A grand classical composition with a full orchestra and elegant melodies."

class MusicGenerator:
    def __init__(self, token=None, output_dir="output_music", model="facebook/musicgen-small"):
        # Initialize the Hugging Face Inference Client with the provided token
        self.client = InferenceClient(token=token)
        # Set output directory, creating it if it doesn't exist
        self.model = model
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def get_music_presets():
        return {preset.name: preset.value for preset in MusicGenerationStyle}

    def generate_music(self, custom_prompt, music_style: MusicGenerationStyle, duration_seconds=10):
        try:
            # Combine the user input prompt with the selected style
            if music_style == MusicGenerationStyle.NONE:
                prompt = custom_prompt
            else:
                prompt = f"{custom_prompt}. in the style of {music_style.value}"

            print(Fore.BLUE + f"Music prompt \t ::-> {prompt}")

            # Generate music using the Hugging Face API
            audio = self.client.text_to_audio(
                prompt,
                model=self.model,
                duration=duration_seconds,  # Duration in seconds
                seed=random.randint(0, 2**32 - 1)
            )

            # Define the output file path
            output_path = os.path.join(self.output_dir, f"{music_style.name}_{uuid.uuid4()}.wav")

            # Save the generated music to the specified output directory
            audio.save(output_path)
            print(Fore.GREEN + f"Music generated successfully and saved to {output_path}.")
            return output_path
        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            sleep(60)  # Retry after a delay
            return None

api_key = "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"  # Reemplaza con tu clave de API
music_generator = MusicGenerator(token=api_key)
output_path = music_generator.generate_music("A happy summer tune with tropical instruments", MusicGenerationStyle.POP, duration_seconds=15)
