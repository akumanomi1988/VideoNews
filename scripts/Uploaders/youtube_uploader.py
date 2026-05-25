import os
import json
import ssl
import time
import google_auth_oauthlib.flow
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

class YoutubeMediaUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self, client_secrets_file, token_file='token.json', channel_description=""):
        try:
            # Define the path for the .secrets directory
            self.secrets_dir = os.path.join(os.getcwd(), ".secrets")
            os.makedirs(self.secrets_dir, exist_ok=True)

            # Full path for the client secrets and token files
            self.client_secrets_file = os.path.join(self.secrets_dir, client_secrets_file)
            self.token_file = os.path.join(self.secrets_dir, token_file)

            self.channel_description = channel_description
            self.youtube = self.authenticate_youtube()
        
        except Exception as e:
            self.handle_error("Error inicializando el uploader", e, True)

    def authenticate_youtube(self):
        """Authenticates the user and returns a YouTube API client."""
        credentials = None
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    print(Fore.CYAN + "Refreshing expired token...")
                    credentials.refresh(Request())
                else:
                    if not os.path.exists(self.client_secrets_file):
                        raise FileNotFoundError(f"Archivo de client secrets no encontrado: {self.client_secrets_file}")

                    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.SCOPES)
                    print(Fore.CYAN + "Running authorization flow on local server...")
                    credentials = flow.run_local_server(port=0)

                    # Save the credentials for future use
                    with open(self.token_file, 'w') as token:
                        token.write(credentials.to_json())

            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            print(Fore.GREEN + "Authentication successful!")
            return youtube
        
        except Exception as e:
            self.handle_error("Error en autenticación", e, True)
            raise

    def upload(self, video_path, title, description, tags, thumbnail_path=None, default_language='es', privacy_status='public'):
        try:
            self.validate_short_parameters(video_path, title, description, tags, default_language, privacy_status)

            hashtags = [f"{tag}" for tag in tags]
            full_description = f"{description}\n\n{self.channel_description}\n\n{' #'.join(hashtags)}\n\n#Shorts #news #breakingnews"
            
            print(Fore.CYAN + f"Uploading Short with title: '{title}'...")
            
            media = MediaFileUpload(
                    video_path,
                    chunksize=1024*1024*8,  # 8MB chunks
                    resumable=True,
                    mimetype='video/mp4'
            )

            request = self.youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title[:90],
                        "description": full_description,
                        "tags": hashtags,
                        "categoryId": "25",
                        "defaultLanguage": default_language,
                        "defaultAudioLanguage": default_language,
                    },
                    "status": {
                        "privacyStatus": privacy_status,
                        "selfDeclaredMadeForKids": False,
                        "license": "youtube",
                        "embeddable": True,
                        "publicStatsViewable": True,
                    }
                },
                media_body=media
            )
            
            response = self.execute_request_with_retries(request)

            if thumbnail_path:
                self.set_thumbnail(response['id'], thumbnail_path)

            print(Fore.GREEN + f"Short uploaded successfully: {title}")
            return response
        
        except Exception as e:
            self.handle_error(f"Error subiendo video: {title}", e, True)
            raise

    def validate_short_parameters(self, video_path, title, description, tags, default_language, privacy_status):
        """Validates parameters for short video uploads."""
        try:
            if not os.path.isfile(video_path):
                raise ValueError(f"El archivo de video no existe: {video_path}")
            
            if not title or len(title.strip()) == 0:
                raise ValueError("El título no puede estar vacío")
            
            if len(title) > 100:
                raise ValueError(f"Título demasiado largo ({len(title)} caracteres). Máximo permitido: 100 caracteres")
            
            if len(description) > 5000:
                raise ValueError(f"Descripción demasiado larga ({len(description)} caracteres). Máximo permitido: 5000 caracteres")
            
            if not isinstance(tags, list):
                raise ValueError(f"Los tags deben ser una lista. Tipo recibido: {type(tags)}")
            
            if len(tags) > 30:
                raise ValueError(f"Demasiados tags ({len(tags)}). Máximo permitido: 30 tags")
            
            invalid_tags = [tag for tag in tags if not isinstance(tag, str)]
            if invalid_tags:
                raise ValueError(f"Tags inválidos (deben ser strings): {invalid_tags}")
            
            valid_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko']
            if default_language not in valid_languages:
                raise ValueError(f"Idioma inválido: {default_language}. Opciones válidas: {', '.join(valid_languages)}")
            
            if privacy_status not in ["public", "private", "unlisted"]:
                raise ValueError(f"Estado de privacidad inválido: {privacy_status}. Opciones válidas: public, private, unlisted")
        
        except Exception as e:
            self.handle_error("Validación fallida", e, True)
            raise

    def execute_request_with_retries(self, request, max_attempts=5):
        """Executes a request with retry logic in case of temporary errors."""
        for attempt in range(max_attempts):
            try:
                return request.execute()
            
            except HttpError as e:
                error_details = self.parse_http_error(e)
                print(Fore.RED + f"Error en la API (Intento {attempt + 1}/{max_attempts}):")
                print(Fore.RED + f"HTTP Status: {e.resp.status}")
                print(Fore.RED + f"Error Details: {error_details}")
                
                if e.resp.status in [403, 429]:  # Quota exceeded or rate limit
                    wait_time = 2 ** (attempt + 1)
                    print(Fore.YELLOW + f"Esperando {wait_time} segundos antes de reintentar...")
                    time.sleep(wait_time)
                else:
                    raise
            
            except ssl.SSLEOFError as e:
                print(Fore.RED + f"Error de conexión SSL (Intento {attempt + 1}/{max_attempts}): {str(e)}")
                print(Fore.YELLOW + "Verifique su conexión a internet y reintentando...")
                time.sleep(5)
            
            except Exception as e:
                self.handle_error("Error inesperado en la solicitud", e)
                raise
        
        raise Exception(Fore.RED + f"Fallo después de {max_attempts} intentos")

    def parse_http_error(self, error):
        """Parse HTTP error response for detailed information."""
        try:
            error_content = error.content.decode()
            error_json = json.loads(error_content)
            return {
                'code': error.resp.status,
                'message': error_json.get('error', {}).get('message', 'Unknown error'),
                'errors': error_json.get('error', {}).get('errors', []),
                'reason': error_json.get('error', {}).get('errors', [{}])[0].get('reason', 'Unknown')
            }
        except Exception as e:
            return f"No se pudo parsear el error: {str(e)}. Contenido crudo: {error.content}"

    def set_thumbnail(self, video_id, thumbnail_path):
        try:
            if not os.path.isfile(thumbnail_path):
                raise FileNotFoundError(f"Archivo de thumbnail no encontrado: {thumbnail_path}")

            max_size = 2 * 1024 * 1024
            size = os.path.getsize(thumbnail_path)
            if size > max_size:
                from PIL import Image
                img = Image.open(thumbnail_path)
                img.save(thumbnail_path, quality=85, optimize=True)
                size = os.path.getsize(thumbnail_path)
                while size > max_size:
                    img = Image.open(thumbnail_path)
                    w, h = img.size
                    img = img.resize((int(w * 0.8), int(h * 0.8)), Image.LANCZOS)
                    img.save(thumbnail_path, quality=80, optimize=True)
                    size = os.path.getsize(thumbnail_path)

            print(Fore.CYAN + f"Setting thumbnail for video ID: {video_id}")
            media = MediaFileUpload(thumbnail_path, resumable=True)
            request = self.youtube.thumbnails().set(videoId=video_id, media_body=media)
            response = self.execute_request_with_retries(request)

            print(Fore.GREEN + f"Thumbnail set for video ID: {video_id}")
            return response

        except Exception as e:
            self.handle_error(f"Error estableciendo thumbnail para video {video_id}", e, True)
            raise

    def handle_error(self, context, error, critical=False):
        """Maneja y muestra errores de forma consistente."""
        error_type = type(error).__name__
        error_message = str(error)

        def safe_print(text):
            try:
                print(text)
            except UnicodeEncodeError:
                print(text.encode('ascii', 'replace').decode('ascii'))
        
        safe_print(Fore.RED + Style.BRIGHT + f"\n[!] ERROR: {context}")
        safe_print(Fore.RED + f"Tipo: {error_type}")
        safe_print(Fore.RED + f"Mensaje: {error_message}")

        if isinstance(error, HttpError):
            error_details = self.parse_http_error(error)
            safe_print(Fore.RED + f"Detalles API: {json.dumps(error_details, indent=2)}")

        if critical:
            safe_print(Fore.RED + Style.BRIGHT + "[X] Error critico, deteniendo ejecucion")
            raise
        else:
            safe_print(Fore.YELLOW + "[>] Continuando despues de error no critico")
