import requests
import os
import uuid
import configparser

class PexelsMediaFetcher:
    def __init__(self):
        self.api_key = self.load_pexels_api_key()
        self.headers = {"Authorization": self.api_key}
        self.temp_dir = ".temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def load_pexels_api_key(self):
        config = configparser.ConfigParser()
        config.read('settings.config')
        return config['PexelsAPI']['API_KEY']

    def fetch_and_save_media(self, query, media_type="video"):
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1&media_type={media_type}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            media_data = response.json()
            for media in media_data.get('videos', media_data.get('photos', [])):
                file_url = media['video_files'][0]['link'] if media_type == "video" else media['src']['original']
                file_ext = file_url.split('.')[-1]
                file_name = f"{uuid.uuid4()}.{file_ext}"
                file_path = os.path.join(self.temp_dir, file_name)
                
                with requests.get(file_url, stream=True) as r:
                    with open(file_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                return file_path
        else:
            print(f"Failed to fetch media for query '{query}'. Status code: {response.status_code}")
            return None
