# API Integration Documentation

## News APIs

### NewsAPI Integration
- **Endpoint**: `https://newsapi.org/v2/`
- **Authentication**: API key in header
- **Rate Limits**: 
  - Free: 100 requests/day
  - Business: 20,000 requests/day

#### Available Endpoints
```python
/top-headlines
/everything
/sources
```

### Currents API Integration
- **Endpoint**: `https://api.currentsapi.services/v1/`
- **Authentication**: API key in query parameters
- **Features**:
  - Latest news retrieval
  - Category filtering
  - Language selection

## Media Services

### Pexels API
- **Endpoint**: `https://api.pexels.com/v1/`
- **Authentication**: API key in header
- **Features**:
  - Image search
  - Video search
  - Collections access

### ElevenLabs API
- **Base URL**: `https://api.elevenlabs.io/v1/`
- **Authentication**: API key in header
- **Features**:
  - Text-to-speech conversion
  - Voice cloning
  - Voice management
  - Usage monitoring

#### Voice Management Endpoints
```python
/voices
/voices/{voice_id}
/voices/settings
```

## Social Media Integration

### YouTube API
- **OAuth 2.0 Authentication**
- **Scopes**:
  ```python
  'https://www.googleapis.com/auth/youtube.upload'
  'https://www.googleapis.com/auth/youtube'
  ```
- **Features**:
  - Video upload
  - Metadata management
  - Playlist handling

### TikTok API
- **Authentication**: OAuth 2.0
- **Required Permissions**:
  - Video upload
  - Video management
  - Account stats

## Telegram Integration

### Bot API
- **Base URL**: `https://api.telegram.org/bot{token}/`
- **Features**:
  - Command handling
  - User management
  - Media sharing
  - Progress updates

### Webhook Configuration
```python
{
    "url": "https://akumanomi1988.example.com/webhook",
    "allowed_updates": ["message", "callback_query"],
    "max_connections": 100
}
```

## Error Handling

### Rate Limiting
```python
class RateLimitHandler:
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def can_make_request(self):
        now = time.time()
        self.requests = [req for req in self.requests if now - req < self.time_window]
        return len(self.requests) < self.max_requests
```

### Retry Strategy
```python
@retry_with_backoff(
    retries=3,
    backoff_in_seconds=2,
    exceptions=(RequestException,)
)
def make_api_request():
    # API call implementation
    pass
```

## Authentication

### API Key Management
```json
{
    "news_api": {
        "key": "YOUR_NEWS_API_KEY",
        "type": "header",
        "header_name": "X-Api-Key"
    },
    "elevenlabs": {
        "key": "YOUR_ELEVENLABS_KEY",
        "type": "header",
        "header_name": "xi-api-key"
    }
}
```

### OAuth Configuration
```json
{
    "youtube": {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uri": "YOUR_REDIRECT_URI",
        "scopes": [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube"
        ]
    }
}
```

## Data Formats

### Video Upload Format
```json
{
    "title": "Video Title",
    "description": "Video Description",
    "tags": ["tag1", "tag2"],
    "categoryId": "22",
    "privacyStatus": "public",
    "language": "en"
}
```

### News Article Format
```json
{
    "url": "article_url",
    "title": "Article Title",
    "description": "Article Description",
    "content": "Full Article Content",
    "publishedAt": "2025-05-10T12:00:00Z",
    "source": {
        "id": "source_id",
        "name": "Source Name"
    }
}
```

## Usage Examples

### News Fetching
```python
async def fetch_news(category: str, language: str) -> List[Article]:
    headers = {"X-Api-Key": config.NEWS_API_KEY}
    params = {
        "category": category,
        "language": language,
        "pageSize": 10
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(NEWS_API_ENDPOINT, headers=headers, params=params) as response:
            data = await response.json()
            return [Article(**article) for article in data["articles"]]
```

### Video Upload
```python
def upload_video(video_path: str, metadata: dict) -> str:
    youtube = build_youtube_client()
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "categoryId": metadata["categoryId"]
            },
            "status": {
                "privacyStatus": metadata["privacyStatus"],
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(video_path)
    )
    response = request.execute()
    return f"https://youtu.be/{response['id']}"
```

## Security Considerations

### API Key Protection
- Store keys in environment variables
- Use secret management systems
- Implement key rotation

### OAuth Security
- Use HTTPS only
- Implement PKCE for mobile
- Store tokens securely
- Refresh token handling

### Rate Limit Compliance
- Implement request queuing
- Track usage metrics
- Handle rate limit errors