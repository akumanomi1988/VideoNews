import moviepy.editor as mp
import configparser
import os

class VideoAssembler:
    def __init__(self, media_files, subtitle_file, voiceover_file, output_file):
        self.media_files = media_files
        self.subtitle_file = subtitle_file
        self.voiceover_file = voiceover_file
        self.output_file = output_file
        self.settings = self.load_settings()
        self.aspect_ratio = self.settings.get('aspect_ratio', '16:9')
        self.background_music = self.settings.get('background_music', '')

    def load_settings(self):
        config = configparser.ConfigParser()
        config.read('settings.config')
        return config['Settings']

    def adjust_aspect_ratio(self, video_clip, target_aspect_ratio):
        w, h = video_clip.size
        if target_aspect_ratio == '16:9':
            target_w = 16
            target_h = 9
        else:
            target_w = 9
            target_h = 16
        
        # Calculate the new dimensions
        if w / h > target_w / target_h:
            new_w = int(h * (target_w / target_h))
            new_h = h
        else:
            new_w = w
            new_h = int(w * (target_h / target_w))
        
        return video_clip.resize(newsize=(new_w, new_h)).crop(x_center=new_w / 2, y_center=new_h / 2, width=w, height=h)

    def adjust_videos(self):
        adjusted_files = []
        for media_file in self.media_files:
            clip = mp.VideoFileClip(media_file)
            adjusted_clip = self.adjust_aspect_ratio(clip, self.aspect_ratio)
            adjusted_file = os.path.join(".temp", os.path.basename(media_file))
            adjusted_clip.write_videofile(adjusted_file, codec="libx264", audio_codec="aac")
            adjusted_files.append(adjusted_file)
        return adjusted_files

    def assemble_video(self):
        adjusted_files = self.adjust_videos()
        clips = [mp.VideoFileClip(mf) for mf in adjusted_files]
        video = mp.concatenate_videoclips(clips, method="compose")
        
        # Load voiceover and adjust the duration of the video
        audio = mp.AudioFileClip(self.voiceover_file)
        video_duration = audio.duration
        video = video.set_audio(audio)
        
        # Repeat or trim the video to match the audio duration
        video = video.fx(mp.vfx.loop, duration=video_duration)
        
        # Add background music if specified
        if self.background_music:
            music = mp.AudioFileClip(self.background_music)
            background_audio = mp.CompositeAudioClip([audio, music.volumex(0.2)])
            video = video.set_audio(background_audio)
        
        # Add subtitles if specified
        if self.subtitle_file:
            subtitles = mp.TextClip(self.subtitle_file, fontsize=24, color='white', bg_color='black')
            subtitles = subtitles.set_pos(('center', 'bottom')).set_duration(video_duration)
            video = mp.CompositeVideoClip([video, subtitles])
        
        video.write_videofile(self.output_file, codec="libx264", audio_codec="aac")
