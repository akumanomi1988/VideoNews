import os
import json
import ssl
import time
import logging
import webbrowser
import google_auth_oauthlib.flow
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

log = logging.getLogger(__name__)


class _WindowsDefaultBrowser:
    """Open OAuth consent through the Windows URL handler, with a Python fallback."""

    def open(self, url, new=0, autoraise=True):
        if os.name == "nt":
            try:
                os.startfile(url)
                return True
            except OSError:
                log.debug("Windows URL handler could not open the OAuth page", exc_info=True)

        opened = webbrowser.open(url, new=new, autoraise=autoraise)
        if not opened:
            raise RuntimeError("Could not open the Google authorization page in a browser")
        return True

class YoutubeMediaUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube.readonly"]

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

    def safe_print(self, text):
        try:
            print(text)
        except UnicodeEncodeError:
            print(text.encode('ascii', 'replace').decode('ascii'))

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

                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.SCOPES)
                    print(Fore.CYAN + "Opening Google authorization in your default browser...")
                    # The port and PKCE state are generated for this live local-server
                    # session. Never ask the user to reconstruct or reuse a copied URL.
                    browser_name = "videonews-windows-default"
                    webbrowser.register(browser_name, None, _WindowsDefaultBrowser())
                    credentials = flow.run_local_server(
                        port=0,
                        open_browser=True,
                        browser=browser_name,
                        authorization_prompt_message=(
                            "If the browser did not open, check the local browser-launch error."
                        ),
                    )

                    # Save the credentials for future use
                    with open(self.token_file, 'w') as token:
                        token.write(credentials.to_json())

            youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            print(Fore.GREEN + "Authentication successful!")
            return youtube
        
        except Exception as e:
            self.handle_error("Error en autenticación", e, True)
            raise

    def get_channel_id(self):
        """Return the channel bound to the currently authorized OAuth token."""
        return self.get_channel_info()["id"]

    def get_channel_info(self):
        """Return the authenticated channel identity and display name."""
        response = self.youtube.channels().list(part="id,snippet", mine=True).execute()
        items = response.get("items", [])
        if len(items) != 1 or not items[0].get("id") or not items[0].get("snippet", {}).get("title"):
            raise RuntimeError("Could not identify the authorized YouTube channel")
        return {"id": str(items[0]["id"]),
                "title": str(items[0]["snippet"]["title"])}

    def verify_video(self, video_id, expected_channel_id, expected_privacy_status):
        """Read the inserted video back and verify channel and effective visibility."""
        response = self.youtube.videos().list(
            part="status,snippet", id=video_id).execute()
        items = response.get("items", [])
        if len(items) != 1:
            raise RuntimeError("YouTube did not return the uploaded video for verification")
        video = items[0]
        actual_privacy = video.get("status", {}).get("privacyStatus")
        actual_channel = video.get("snippet", {}).get("channelId")
        if actual_channel != expected_channel_id:
            raise RuntimeError("Uploaded video belongs to a different YouTube channel")
        if actual_privacy != expected_privacy_status:
            raise RuntimeError("YouTube privacy verification did not match the requested status")
        return {"video_id": str(video_id), "channel_id": actual_channel,
                "privacy_status": actual_privacy}

    def upload(self, video_path, title, description, tags, thumbnail_path=None, default_language='es', privacy_status='private', contains_synthetic_media=False):
        stage = "metadata_preflight"
        try:
            self.validate_short_parameters(video_path, title, description, tags, default_language, privacy_status)
            if thumbnail_path:
                stage = "thumbnail_preflight"
                self.validate_thumbnail(thumbnail_path)

            import re
            seen = set()
            sanitized = []
            for tag in tags:
                clean = re.sub(r'[^\w\s-]', '', tag).strip().lower()
                clean = re.sub(r'\s+', ' ', clean)[:60]
                if clean and len(clean) >= 3 and clean not in seen and not clean.isdigit():
                    seen.add(clean)
                    sanitized.append(clean)
            total = 0
            final_tags = []
            for tag in sanitized:
                if len(final_tags) >= 15:
                    break
                if total + len(tag) + 1 <= 500:
                    final_tags.append(tag)
                    total += len(tag) + 1
            sanitized = final_tags
            log.info(f"YouTube tags ({len(sanitized)}, {total}c): {sanitized[:5]}...")

            tag_line = f"\n\n{' #'.join(sanitized)}" if sanitized else ""

            desc_candidates = [
                description,
                re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', description),
                re.sub(r'[^\x20-\x7E\n\r\t\s]', '', description),
                f"{title[:200]}",
            ]
            desc_candidates = [d for d in desc_candidates if d]

            for idx, desc in enumerate(desc_candidates):
                full = f"{desc}\n\n{self.channel_description}{tag_line}"
                full = re.sub(r'\n{3,}', '\n\n', full.strip())[:5000]
                self.safe_print(Fore.CYAN + f"Uploading Short with title: '{title[:60]}'...")

                media = MediaFileUpload(
                    video_path,
                    chunksize=1024*1024*8,
                    resumable=True,
                    mimetype='video/mp4'
                )

                stage = "build_videos_insert_request"
                request = self.youtube.videos().insert(
                    part="snippet,status",
                    body={
                        "snippet": {
                            "title": title[:90],
                            "description": full,
                            "tags": sanitized,
                            "categoryId": "25",
                            "defaultLanguage": default_language,
                        },
                        "status": {
                            "privacyStatus": privacy_status,
                            "selfDeclaredMadeForKids": False,
                            "containsSyntheticMedia": bool(contains_synthetic_media),
                            "license": "youtube",
                            "embeddable": True,
                            "publicStatsViewable": True,
                        }
                    },
                    media_body=media
                )

                try:
                    # Upload outcomes can be ambiguous after a network break. Let
                    # Studio persist upload_unknown and require reconciliation;
                    # never replay a video insert automatically.
                    stage = "execute_videos_insert_request"
                    response = request.execute()
                    break
                except HttpError as e:
                    if e.resp.status == 400 and 'invalidDescription' in str(e):
                        log.warning(f"Description attempt {idx+1} rejected, trying simpler version")
                        continue
                    raise
            else:
                raise RuntimeError("All description candidates rejected by YouTube API")

            if thumbnail_path:
                try:
                    self.set_thumbnail(response['id'], thumbnail_path)
                except Exception as thumbnail_error:
                    # The video insert already returned an ID; do not turn a
                    # thumbnail failure into an ambiguous upload that may be retried.
                    log.warning("Video uploaded, but thumbnail update failed: %s", thumbnail_error)
                    response['thumbnail_warning'] = str(thumbnail_error)[:500]

            self.safe_print(Fore.GREEN + f"Short uploaded successfully: {title[:60]}")
            return response
        
        except Exception as e:
            log.exception("YouTube video.insert failed at stage=%s", stage)
            raise RuntimeError(
                f"YouTube video.insert failed at {stage}: {type(e).__name__}: {e}"
            ) from e

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
                log.warning(f"Descripción larga ({len(description)} chars), se truncará en full_description")
            
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
            
            if privacy_status not in ("public", "private", "unlisted"):
                raise ValueError("privacy_status must be public, private, or unlisted")
        
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
                    reason = error_details.get('reason', '')
                    if reason == 'quotaExceeded':
                        print(Fore.RED + "❌ YouTube quota exceeded. Cannot upload.")
                        raise
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

            self.validate_thumbnail(thumbnail_path)

            print(Fore.CYAN + f"Setting thumbnail for video ID: {video_id}")
            from PIL import Image
            with Image.open(thumbnail_path) as image:
                mime_type = "image/jpeg" if image.format == "JPEG" else "image/png"
            media = MediaFileUpload(thumbnail_path, mimetype=mime_type, resumable=True)
            request = self.youtube.thumbnails().set(videoId=video_id, media_body=media)
            response = self.execute_request_with_retries(request)

            print(Fore.GREEN + f"Thumbnail set for video ID: {video_id}")
            return response

        except Exception as e:
            self.handle_error(f"Error estableciendo thumbnail para video {video_id}", e, True)
            raise

    @staticmethod
    def validate_thumbnail(thumbnail_path, expected_aspect=None):
        """Validate a custom thumbnail before starting a non-idempotent video insert."""
        from PIL import Image

        if not os.path.isfile(thumbnail_path):
            raise FileNotFoundError(f"Archivo de thumbnail no encontrado: {thumbnail_path}")
        size_bytes = os.path.getsize(thumbnail_path)
        if size_bytes <= 0 or size_bytes > 50 * 1024 * 1024:
            raise ValueError("YouTube thumbnails must be non-empty and at most 50 MB")
        try:
            with Image.open(thumbnail_path) as image:
                image_format = image.format
                width, height = image.size
                image.verify()
        except Exception as exc:
            raise ValueError("Thumbnail is not a valid JPEG or PNG image") from exc
        if image_format not in ("JPEG", "PNG"):
            raise ValueError("YouTube thumbnails must use JPEG or PNG format")
        minimum = 640
        if width >= height and width < minimum:
            raise ValueError("Landscape video thumbnails must be at least 640 pixels wide")
        if height > width and height < minimum:
            raise ValueError("Portrait video thumbnails must be at least 640 pixels tall")
        if expected_aspect in ("16:9", "9:16"):
            target = 16 / 9 if expected_aspect == "16:9" else 9 / 16
            if abs((width / height) - target) > 0.03:
                raise ValueError(f"Thumbnail aspect ratio must match {expected_aspect}")

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
