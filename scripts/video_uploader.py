from googleapiclient.discovery import build
import tiktokapi

class VideoUploader:
    def __init__(self, youtube_api_key, tiktok_api_key):
        self.youtube_api_key = youtube_api_key
        self.tiktok_api_key = tiktok_api_key

    def upload_to_youtube(self, video_path, title, description, tags):
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
            media_body=video_path
        )
        response = request.execute()
        return response

    def upload_to_tiktok(self, video_path, description):
        api = tiktokapi.TikTokAPI(api_key=self.tiktok_api_key)
        response = api.upload_video(video_path, description=description)
        return response
