import whisper
import os
import uuid
import configparser

class SubtitleAndVoiceGenerator:
    def __init__(self, article_text):
        self.article_text = article_text
        self.language = self.load_language()

    def load_language(self):
        config = configparser.ConfigParser()
        config.read('settings.config')
        return config['LanguageSettings']['LANGUAGE']

    def generate_subtitles(self):
        subtitle_path = os.path.join(".temp", f"{uuid.uuid4()}.srt")
        with open(subtitle_path, "w") as f:
            f.write(self.article_text)
        return subtitle_path

    def generate_voiceover(self):
        model = whisper.load_model("base")
        voiceover_path = os.path.join(".temp", f"{uuid.uuid4()}.wav")
        result = model.transcribe(text=self.article_text, language=self.language)
        with open(voiceover_path, "wb") as f:
            f.write(result["audio"].tobytes())
        return voiceover_path
