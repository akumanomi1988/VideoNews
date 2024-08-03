import requests
import config

def upload_to_youtube(video_path, title, description):
    headers = {
        'Authorization': f'Bearer {config.YOUTUBE_API_KEY}',
        'Content-Type': 'application/json'
    }
    video_data = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': ['tendencias', 'twitter'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'public'
        }
    }
    files = {
        'video': open(video_path, 'rb')
    }
    response = requests.post('https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable', headers=headers, files=files)
    return response.json()
