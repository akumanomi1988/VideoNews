from gtts import gTTS

def create_audio(text, filename="output.mp3"):
    tts = gTTS(text=text, lang='es', tld='es')  # 'es' para español de España
    tts.save(filename)
