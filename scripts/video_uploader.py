import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

class VideoUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self, client_secrets_file, channel_description, tiktok_api_key=None):
        self.client_secrets_file = client_secrets_file
        self.channel_description = channel_description
        self.tiktok_api_key = tiktok_api_key
        self.youtube = self.authenticate_youtube()

    def authenticate_youtube(self):
        # Desactivar la verificación HTTPS de OAuthlib cuando se ejecuta localmente
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Obtener credenciales y crear un cliente de la API
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.SCOPES)
        
        # Ejecutar el flujo de autorización en un servidor local
        credentials = flow.run_local_server(port=0)
        
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", credentials=credentials)
        
        return youtube

    def upload_to_youtube(self, video_path, title, description, tags):
        # Añadir # delante de cada tag
        hashtags = [f"#{tag}" for tag in tags]
        
        # Concatenar la descripción del video con la descripción del canal y los hashtags
        full_description = f"{description}\n\n{self.channel_description}\n\n{' '.join(hashtags)}"
        
        # Configurar la subida del video
        media = MediaFileUpload(video_path)
        request = self.youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": full_description,
                    "tags": hashtags
                },
                "status": {
                    "privacyStatus": "public"
                }
            },
            media_body=media
        )
        response = request.execute()
        return response
