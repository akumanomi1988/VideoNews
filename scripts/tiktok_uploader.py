import requests
import json

class TikTokUploader:
    def __init__(self, session_id):
        self.session_id = session_id
        self.base_url = "https://www.tiktok.com/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Cookie": f"sessionid={session_id}"
        }

    def upload_video(self, video_path, description, tags):
        # Paso 1: Iniciar la carga del video
        upload_url = f"{self.base_url}/v1/video/upload/"
        with open(video_path, "rb") as video_file:
            files = {"video": ("video.mp4", video_file, "video/mp4")}
            response = requests.post(upload_url, headers=self.headers, files=files)
        
        if response.status_code != 200:
            raise Exception("Error al iniciar la carga del video")

        video_id = response.json().get("video_id")

        # Paso 2: Publicar el video
        publish_url = f"{self.base_url}/v1/video/create/"
        data = {
            "video_id": video_id,
            "description": description,
            "privacy_level": "public",
            "allow_comment": 1,
            "allow_duet": 1,
            "allow_react": 1,
            "social_cover": 0
        }

        if tags:
            data["hashtag_names"] = json.dumps(tags)

        response = requests.post(publish_url, headers=self.headers, json=data)

        if response.status_code != 200:
            raise Exception("Error al publicar el video")

        return response.json()

# # Uso de la clase
# uploader = TikTokUploader("tu_session_id_aqui")
# result = uploader.upload_video("ruta_del_video.mp4", "Descripción del video", ["tag1", "tag2"])
# print(result)