"""TikTok Content Posting API v2: upload to creator inbox.

Users must approve/finish the post inside TikTok. Direct posting requires
additional consent and app approval; this module does not silently publish.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import requests

API_BASE = "https://open.tiktokapis.com/v2"
CHUNK_SIZE = 32 * 1024 * 1024


class TiktokMediaUploader:
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, token_file=None):
        self.client_id = client_id or os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = client_secret or os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("TIKTOK_REDIRECT_URI", "")
        self.token_file = Path(token_file or os.getenv("TIKTOK_TOKEN_FILE", ".secrets/tiktok_token.json"))
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.refresh_token = os.getenv("TIKTOK_REFRESH_TOKEN", "")
        self.load_tokens()

    def load_tokens(self):
        if self.token_file.is_file():
            data = json.loads(self.token_file.read_text(encoding="utf-8"))
            self.access_token = data.get("access_token", self.access_token)
            self.refresh_token = data.get("refresh_token", self.refresh_token)

    def save_tokens(self):
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"access_token": self.access_token, "refresh_token": self.refresh_token}
        fd = os.open(str(self.token_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream)

    def authenticate(self, state: str):
        """Build OAuth authorization URL. Caller must generate and validate state."""
        if not self.client_id or not self.redirect_uri or not state:
            raise ValueError("TikTok client key, redirect URI and CSRF state are required")
        return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
            "client_key": self.client_id,
            "scope": "video.upload",
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
        })

    def exchange_code(self, code: str):
        """Only exchange a code after the web callback has verified OAuth state."""
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise ValueError("TikTok OAuth client credentials are not configured")
        response = requests.post(API_BASE + "/oauth/token/", data={
            "client_key": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data.get("access_token"):
            raise RuntimeError("TikTok authorization failed")
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", "")
        self.save_tokens()

    def refresh_access_token(self):
        if not all((self.client_id, self.client_secret, self.refresh_token)):
            raise ValueError("TikTok refresh credentials are missing")
        response = requests.post(API_BASE + "/oauth/token/", data={
            "client_key": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data.get("access_token"):
            raise RuntimeError("TikTok token refresh failed")
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.save_tokens()

    def upload_media(self, media_path):
        """Transfer MP4 to creator inbox and return publish ID, not a public URL."""
        if not self.access_token:
            raise ValueError("TikTok requires a user access token with video.upload scope")
        file_path = Path(media_path)
        size = file_path.stat().st_size
        if size == 0:
            raise ValueError("Cannot upload an empty video")
        chunk = min(CHUNK_SIZE, size)
        count = max(1, (size + chunk - 1) // chunk)
        response = requests.post(
            API_BASE + "/post/publish/inbox/video/init/",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk,
                "total_chunk_count": count,
            }},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTok rejected upload: {payload.get('error', {}).get('code', 'unknown')}")
        data = payload.get("data") or {}
        upload_url = data.get("upload_url", "")
        hostname = (urlsplit(upload_url).hostname or "").lower()
        if urlsplit(upload_url).scheme != "https" or hostname != "open-upload.tiktokapis.com":
            raise ValueError("Unexpected TikTok upload host")
        with file_path.open("rb") as stream:
            offset = 0
            for index in range(count):
                length = size - offset if index == count - 1 else chunk
                part = stream.read(length)
                if len(part) != length:
                    raise OSError("Could not read complete video chunk")
                result = requests.put(
                    upload_url, data=part,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(length),
                        "Content-Range": f"bytes {offset}-{offset + length - 1}/{size}",
                    }, timeout=180,
                )
                if result.status_code not in (201, 206):
                    result.raise_for_status()
                    raise RuntimeError("TikTok media transfer was not accepted")
                offset += length
        return {"publish_id": data.get("publish_id"), "status": "pending_creator_confirmation"}
