from pydub import AudioSegment
import moviepy.editor as mp
import os
from colorama import init, Fore

# Initialize colorama
init(autoreset=True)

class AudioManager:
    """Handles audio processing, including voiceovers and background music."""

    def __init__(self, voiceover_file, background_music=""):
        self.voiceover_file = voiceover_file
        self.background_music = background_music

    def get_voiceover_audio(self):
        """Load and return the voiceover audio file."""
        try:
            audio = mp.AudioFileClip(self.voiceover_file).audio_fadeout(2)
            return audio
        except Exception as e:
            raise ValueError(Fore.RED + f"❌ Error loading voiceover: {e}")

    def add_background_music(self, video, audio_duration):
        """Add background music to the video."""
        if self.background_music:
            try:
                music = AudioSegment.from_mp3(self.background_music)
                temp_music_file = os.path.join(".temp", "temp_music.wav")
                music.export(temp_music_file, format="wav")

                with mp.AudioFileClip(temp_music_file) as music_clip:
                    music_clip = music_clip.volumex(0.2).subclip(0, audio_duration).audio_fadeout(2)
                    composite_audio = mp.CompositeAudioClip([video.audio, music_clip])
                    video = video.set_audio(composite_audio)
            except Exception as e:
                raise ValueError(Fore.RED + f"❌ Error processing background music: {e}")
        return video
