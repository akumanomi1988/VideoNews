import moviepy.editor as mp
import os
import configparser
from googleapiclient.discovery import build

class LongVideoCompiler:
    def __init__(self, video_files, output_file):
        self.video_files = video_files
        self.output_file = output_file
        self.config = self.load_config()
        self.youtube_api_key = self.config['YouTubeAPI']['API_KEY']
    
    def load_config(self):
        config = configparser.ConfigParser()
        config.read('settings.config')
        return config

    def compile_video(self):
        # Crear una lista de clips de video
        clips = [mp.VideoFileClip(file) for file in self.video_files]
        
        # Concatenar los clips
        final_video = mp.concatenate_videoclips(clips, method="compose")
        
        # Exportar el video compilado
        final_video.write_videofile(self.output_file, codec="libx264", audio_codec="aac")

    def upload_to_youtube(self, title, description, tags):
        youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags
                },
                "status": {
                    "privacyStatus": "public"
                }
            },
            media_body=self.output_file
        )
        response = request.execute()
        return response
