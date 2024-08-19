import moviepy.editor as mp

class VideoAssembler:
    def __init__(self, media_files, subtitle_file, voiceover_file, output_file):
        self.media_files = media_files
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file

    def assemble_video(self):
        clips = [mp.VideoFileClip(mf) for mf in self.media_files]
        video = mp.concatenate_videoclips(clips, method="compose")
        
        audio = mp.AudioFileClip(self.voiceover_file)
        video = video.set_audio(audio)
        
        video.write_videofile(self.output_file, codec="libx264", audio_codec="aac")
