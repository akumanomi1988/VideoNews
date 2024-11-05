import requests
import json
import os
from flask import Flask, request, redirect

app = Flask(__name__)

class TiktokMediaUploader:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_file = 'token.json'

    def load_tokens(self):
        """Load tokens from a file."""
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
                self.access_token = tokens.get('access_token')
                self.refresh_token = tokens.get('refresh_token')

    def save_tokens(self):
        """Save tokens to a file."""
        tokens = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
        }
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f)

    def authenticate(self):
        """Initiate OAuth 2.0 flow for user authentication."""
        # Build the authorization URL
        auth_url = (
            f"https://open-api.tiktok.com/platform/oauth/connect/"
            f"?client_key={self.client_id}&response_type=code&scope=user.info.basic,video.upload&redirect_uri={self.redirect_uri}"
        )
        print("Please visit the following URL to log in:")
        print(auth_url)
        return auth_url

    @app.route('/callback/', methods=['GET'])
    def callback():
        """Handle the callback from TikTok after user logs in."""
        authorization_code = request.args.get('code')
        if authorization_code:
            # Exchange authorization code for access token
            token_url = "https://open-api.tiktok.com/oauth/access_token/"
            payload = {
                'client_key': self.client_id,
                'client_secret': self.client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            response = requests.post(token_url, data=payload)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['data']['access_token']
                self.refresh_token = data['data']['refresh_token']
                self.save_tokens()
                return "Authentication successful! You can close this window."
            else:
                return f"Error: {response.status_code} - {response.text}"
        else:
            return "Authorization code not received."

    def refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        token_url = "https://open-api.tiktok.com/oauth/refresh_token/"
        payload = {
            'client_key': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['data']['access_token']
            self.refresh_token = data['data']['refresh_token']
            self.save_tokens()
        else:
            print(f"Error refreshing token: {response.status_code} - {response.text}")

    def upload_media(self, media_path):
        """Upload media to TikTok."""
        if not self.access_token:
            print("Access token is required to upload media.")
            return
        
        upload_url = "https://open-api.tiktok.com/media/upload/"
        with open(media_path, 'rb') as media_file:
            files = {'file': media_file}
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            response = requests.post(upload_url, headers=headers, files=files)
            
            if response.status_code == 200:
                print("Media uploaded successfully!")
                print(response.json())
            else:
                print(f"Error uploading media: {response.status_code} - {response.text}")
