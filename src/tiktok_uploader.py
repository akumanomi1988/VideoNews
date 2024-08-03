import requests
import config

def upload_to_tiktok(video_path, title):
    headers = {
        'Authorization': f'Bearer {config.TIKTOK_API_KEY}',
    }
    video_data = {
        'description': title
    }
    files = {
        'video': open(video_path, 'rb')
    }
    response = requests.post('https://open.tiktokapis.com/v1/video/upload', headers=headers, files=files, data=video_data)
    return response.json()
