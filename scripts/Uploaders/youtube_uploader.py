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
        # Define the path for the .secrets directory
        self.secrets_dir = os.path.join(os.getcwd(), ".secrets")
        os.makedirs(self.secrets_dir, exist_ok=True)

        # Full path for the client secrets and token files
        self.client_secrets_file = os.path.join(self.secrets_dir, client_secrets_file)
        self.token_file = os.path.join(self.secrets_dir, token_file)

        self.channel_description = channel_description
        self.youtube = self.authenticate_youtube()

    def authenticate_youtube(self):
        """Authenticates the user and returns a YouTube API client."""
        credentials = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as token:
                token_data = json.load(token)
                credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print(Fore.CYAN + "Refreshing expired token...")
                credentials.refresh(Request())
            else:
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

    def upload_long_video(self, video_path, title, description, tags, thumbnail_path=None, category_id="22", privacy_status="public", location=None, recording_date=None):
        """
        Uploads a long video to YouTube.

        Parameters:
            video_path (str): Path to the video file.
            title (str): Title of the video.
            description (str): Description of the video.
            tags (list): List of tags to include.
            thumbnail_path (str, optional): Path to the thumbnail image file.
            category_id (str, optional): The ID of the video category.
            privacy_status (str, optional): Privacy status of the video.
            location (str, optional): Location where the video was recorded.
            recording_date (str, optional): Recording date of the video in YYYY-MM-DD format.

        Returns:
            dict: The response from the YouTube API.
        """
        # Validate input parameters
        self.validate_video_parameters(video_path, title, description, tags, category_id, privacy_status)

        hashtags = [f"{tag}" for tag in tags]
        full_description = f"{description}\n\n{self.channel_description}\n\n{' '.join(hashtags)}"

        media = MediaFileUpload(video_path)
        print(Fore.CYAN + f"Uploading video '{title}'...")
        
        request = self.youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": full_description,
                    "tags": hashtags,
                    "categoryId": category_id,
                    "location": location or None,
                    "recordingDate": recording_date or None
                },
                "status": {
                    "privacyStatus": privacy_status
                }
            },
            media_body=media
        )
        
        response = self.execute_request_with_retries(request)

        # Optionally set the thumbnail if provided
        if thumbnail_path:
            self.set_thumbnail(response['id'], thumbnail_path)

        print(Fore.GREEN + f"Video uploaded successfully: {title}")
        return response

    def upload_short(self, video_path, title, description, tags, thumbnail_path=None, default_language='es', privacy_status='public'):
        """
        Uploads a short video to YouTube.

        Parameters:
            video_path (str): Path to the video file.
            title (str): Title of the video.
            description (str): Description of the video.
            tags (list): List of tags to include.
            thumbnail_path (str, optional): Path to the thumbnail image file.
            default_language (str, optional): Default language of the video.
            privacy_status (str, optional): Privacy status of the video.

        Returns:
            dict: The response from the YouTube API.
        """
        # Validate input parameters
        self.validate_short_parameters(video_path, title, description, tags, default_language, privacy_status)

        hashtags = [f"{tag}" for tag in tags]
        full_description = f"{description}\n\n{self.channel_description}\n\n{'#'.join(hashtags)}\n\n#Shorts #news #breakingnews"
        
        print(Fore.CYAN + f"Uploading Short with title: '{title}'...")
        
        media = MediaFileUpload(video_path)
        request = self.youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title[:90],  # Truncate title to 90 characters
                    "description": full_description,
                    "tags": hashtags,
                    "categoryId": "25",  # News & Politics
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

        # Optionally set the thumbnail if provided
        if thumbnail_path:
            self.set_thumbnail(response['id'], thumbnail_path)

        print(Fore.GREEN + f"Short uploaded successfully: {title}")
        return response

    def validate_video_parameters(self, video_path, title, description, tags, category_id, privacy_status):
        """Validates parameters for long video uploads."""
        if not os.path.isfile(video_path):
            raise ValueError(Fore.RED + "The video file does not exist.")
        if not title or len(title.strip()) == 0:
            raise ValueError(Fore.RED + "Video title cannot be empty.")
        if len(title) > 100:
            print(Fore.RED + "Video title exceeds 100 characters; it will be truncated.")
            title = title[:100]  # Truncate title if too long
        if len(description) > 5000:
            print(Fore.RED + "Description exceeds 5000 characters; it will be truncated.")
            description = description[:5000]  # Truncate description if too long
        if not isinstance(tags, list):
            raise ValueError(Fore.RED + "Tags must be provided as a list.")
        if not all(isinstance(tag, str) for tag in tags):
            raise ValueError(Fore.RED + "All tags must be strings.")
        if not category_id.isdigit():
            raise ValueError(Fore.RED + "Category ID must be a valid number.")
        if privacy_status not in ["public", "private", "unlisted"]:
            raise ValueError(Fore.RED + "Privacy status must be 'public', 'private', or 'unlisted'.")

    def validate_short_parameters(self, video_path, title, description, tags, default_language, privacy_status):
        """Validates parameters for short video uploads."""
        if not os.path.isfile(video_path):
            raise ValueError(Fore.RED + "The video file does not exist.")
        if not title or len(title.strip()) == 0:
            raise ValueError(Fore.RED + "Short title cannot be empty.")
        if len(title) > 100:
            print(Fore.RED + "Short title exceeds 100 characters; it will be truncated.")
            title = title[:100]
        if len(description) > 5000:
            print(Fore.RED + "Description exceeds 5000 characters; it will be truncated.")
            description = description[:5000]
        if not isinstance(tags, list):
            raise ValueError(Fore.RED + "Tags must be provided as a list.")
        if not all(isinstance(tag, str) for tag in tags):
            raise ValueError(Fore.RED + "All tags must be strings.")
        if default_language not in ['en', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko']:  # Add more as needed
            raise ValueError(Fore.RED + "Default language must be a valid BCP-47 language code.")
        if privacy_status not in ["public", "private", "unlisted"]:
            raise ValueError(Fore.RED + "Privacy status must be 'public', 'private', or 'unlisted'.")

    def execute_request_with_retries(self, request, max_attempts=5):
        """Executes a request with retry logic in case of temporary errors."""
        for attempt in range(max_attempts):
            try:
                return request.execute()
            except (ssl.SSLEOFError, HttpError) as e:
                print(Fore.RED + f"Error: {e}, retrying {attempt + 1}/{max_attempts}..." + Style.RESET_ALL)
                time.sleep(10)  # Wait before retrying
        raise Exception(Fore.RED + "Failed to execute the request after several attempts." + Style.RESET_ALL)

    def set_thumbnail(self, video_id, thumbnail_path):
        """
        Sets a custom thumbnail for a video.

        Parameters:
            video_id (str): The ID of the video.
            thumbnail_path (str): Path to the thumbnail image file.

        Returns:
            dict: The response from the YouTube API.
        """
        if not os.path.isfile(thumbnail_path):
            raise ValueError(Fore.RED + "The thumbnail file does not exist.")
        
        print(Fore.CYAN + f"Setting thumbnail for video ID: {video_id}")
        media = MediaFileUpload(thumbnail_path)
        request = self.youtube.thumbnails().set(videoId=video_id, media_body=media)
        response = request.execute()
        
        print(Fore.GREEN + f"Thumbnail set for video ID: {video_id}")
        return response
