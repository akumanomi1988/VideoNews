import os
from tiktok_uploader.upload import upload_video
from tiktok_uploader.auth import AuthBackend
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

class TikTokVideoUploader:
    def __init__(self, session_id):
        self.session_id = session_id
        self.auth = AuthBackend(sessionid=self.session_id)

    def upload_video(self, video_path, description, tags):
        """
        Uploads a video to TikTok.

        Parameters:
            video_path (str): Path to the video file.
            description (str): Description of the video.
            tags (list): List of tags to include.

        Returns:
            dict: The response from the TikTok upload.
        """
        print(Fore.CYAN + f"Initiating upload for video: {video_path}")

        if not os.path.exists(video_path):
            print(Fore.RED + f"Error: Video file not found at {video_path}")
            return None

        try:
            # Prepare the description with hashtags
            hashtags = " ".join(f"#{tag}" for tag in tags)
            full_description = f"{description}\n\n{hashtags}"

            # Attempt to upload the video
            result = upload_video(video_path, description=full_description, auth=self.auth)

            if result:
                print(Fore.GREEN + f"Video successfully uploaded to TikTok: {video_path}")
                return result
            else:
                print(Fore.RED + "Upload failed. No response received from TikTok.")
                return None

        except Exception as e:
            print(Fore.RED + f"Error occurred during upload: {str(e)}")
            return None

    def validate_session(self):
        """
        Validates the TikTok session.

        Returns:
            bool: True if the session is valid, False otherwise.
        """
        try:
            # Attempt to perform a simple operation to check if the session is valid
            # This could be fetching user info or any other simple API call
            # For now, we'll just check if the session_id is not empty
            if self.session_id:
                print(Fore.GREEN + "TikTok session appears to be valid.")
                return True
            else:
                print(Fore.RED + "TikTok session is not set or invalid.")
                return False
        except Exception as e:
            print(Fore.RED + f"Error validating TikTok session: {str(e)}")
            return False