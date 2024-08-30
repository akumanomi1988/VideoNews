import uuid
from pathlib import Path
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

class TextToSpeech:
    def __init__(self, api_key: str, model_id: str = "eleven_multilingual_v2", voice_id: str = "gD1IexrzCvsXPHUuT0s3"):
        """
        Initializes the class with the API key, model, and voice to use.

        :param api_key: The API key to access Eleven Labs.
        :param model_id: The TTS model to use, default is 'eleven_multilingual_v2'.
        :param voice_id: The voice ID to use, default is gD1IexrzCvsXPHUuT0s3.
        """
        self.api_key = api_key
        self.model_id = model_id
        self.voice_id = voice_id
        self.client = ElevenLabs(api_key=self.api_key)

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
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
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