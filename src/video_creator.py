from moviepy.editor import TextClip, concatenate_videoclips, AudioFileClip

def create_video(text, audio_file):
    text_clip = TextClip(text, fontsize=70, color='white', bg_color='black', size=(1280, 720))
    text_clip = text_clip.set_duration(10)
    audio_clip = AudioFileClip(audio_file)
    video_clip = text_clip.set_audio(audio_clip)
    video_clip.write_videofile("output.mp4", fps=24)
