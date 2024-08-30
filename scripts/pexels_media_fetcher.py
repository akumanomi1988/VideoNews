import requests
import os
import uuid
from colorama import Fore, Style, init

# Inicializar Colorama
init(autoreset=True)

class PexelsMediaFetcher:
    def __init__(self, api_key, temp_dir=".temp"):
        """
        Initializes the PexelsMediaFetcher with the specified API key and temporary directory.

        Parameters:
            api_key (str): The Pexels API key for authentication.
            temp_dir (str): The directory where media files will be saved temporarily.
        """
        self.api_key = api_key
        self.headers = {"Authorization": self.api_key}
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        self.downloaded_video_ids = set()  # To keep track of downloaded video IDs

    def fetch_and_save_media(self, query, media_type="video"):
        """
        Fetches and saves media (video or photo) from Pexels based on the query.

        Parameters:
            query (str): The search query for fetching media.
            media_type (str): The type of media to fetch ('video' or 'photo').

        Returns:
            str: The file path of the saved media, or None if no suitable media is found.
        """
        try:
            if media_type == "video":
                url = f"https://api.pexels.com/videos/search?query={query}&per_page=10"
            elif media_type == "photo":
                url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
            else:
                print(Fore.RED + f"Unsupported media type '{media_type}'.")
                return None

            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()  # Raise an exception for HTTP errors
            except requests.exceptions.RequestException as e:
                print(Fore.RED + f"Failed to fetch {media_type} for query '{query}'. Error: {str(e)}")
                return None

            media_data = response.json()

            if media_type == "video":
                for video in media_data.get('videos', []):
                    try:
                        video_id = video['id']
                        
                        # Skip videos that have already been downloaded
                        if video_id in self.downloaded_video_ids:
                            continue
                        
                        # Check video duration
                        duration = video.get('duration', 0)
                        if duration <= 20:
                            file_url = video['video_files'][0]['link']  # Use the first available video file
                            file_ext = file_url.split('.')[-1].split('?')[0]  # Extract the file extension
                            file_name = f"{uuid.uuid4()}.{file_ext}"
                            file_path = os.path.join(self.temp_dir, file_name)
                            
                            try:
                                with requests.get(file_url, stream=True) as r:
                                    r.raise_for_status()  # Raise an exception for HTTP errors
                                    with open(file_path, 'wb') as f:
                                        for chunk in r.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                
                                # Mark this video as downloaded
                                self.downloaded_video_ids.add(video_id)
                                
                                print(Fore.GREEN + f"Video saved to {file_path}")
                                return file_path
                            except requests.exceptions.RequestException as e:
                                print(Fore.RED + f"Failed to download video '{file_url}'. Error: {str(e)}")
                            except OSError as e:
                                print(Fore.RED + f"Failed to save video file '{file_path}'. Error: {str(e)}")
                    
                    except KeyError as e:
                        print(Fore.RED + f"Missing key in video data: {str(e)}")
                        
                print(Fore.YELLOW + f"No suitable videos found for query '{query}'.")
                return None

            elif media_type == "photo":
                if media_data.get('photos'):
                    photo = media_data['photos'][0]
                    file_url = photo['src']['original']
                    file_ext = file_url.split('.')[-1]
                    file_name = f"{uuid.uuid4()}.{file_ext}"
                    file_path = os.path.join(self.temp_dir, file_name)

                    try:
                        with requests.get(file_url, stream=True) as r:
                            r.raise_for_status()  # Raise an exception for HTTP errors
                            with open(file_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        
                        print(Fore.GREEN + f"Photo saved to {file_path}")
                        return file_path
                    except requests.exceptions.RequestException as e:
                        print(Fore.RED + f"Failed to download photo '{file_url}'. Error: {str(e)}")
                    except OSError as e:
                        print(Fore.RED + f"Failed to save photo file '{file_path}'. Error: {str(e)}")
                else:
                    print(Fore.YELLOW + f"No photos found for query '{query}'.")
                    return None

        except Exception as e:
            print(Fore.RED + f"An unexpected error occurred: {str(e)}")
            return None
