"""OAuth credential lifecycle, endpoint pinning and chunked upload contracts."""
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import pytest
from scripts.Uploaders import tiktok_uploader as tik

@pytest.fixture(autouse=True)
def no_real_tokens(tmp_path, monkeypatch):
    for name in ("TIKTOK_ACCESS_TOKEN", "TIKTOK_REFRESH_TOKEN", "TIKTOK_CLIENT_KEY",
                 "TIKTOK_CLIENT_SECRET", "TIKTOK_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TIKTOK_TOKEN_FILE", str(tmp_path / "never-created.json"))

@pytest.fixture
def uploader(tmp_path):
    return tik.TiktokMediaUploader(token_file=str(tmp_path / "oauth.json"))

def test_missing_access_token_blocks_transfer_before_http(uploader, monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Should not make HTTP requests without OAuth")
    monkeypatch.setattr(tik.requests, "post", forbidden)
    file = tmp_path / "video.mp4"
    file.write_bytes(b"video")
    with pytest.raises(ValueError, match="access token"):
        uploader.upload_media(str(file))

def test_authorization_requires_client_key_and_state(uploader):
    with pytest.raises(ValueError):
        uploader.authenticate("state")
    uploader.client_id = "client"
    uploader.redirect_uri = "https://example.org/callback"
    with pytest.raises(ValueError):
        uploader.authenticate("")

def test_authorization_url_contains_oauth_csrf_state(uploader):
    uploader.client_id = "client-id"
    uploader.redirect_uri = "https://example.org/callback"
    url = uploader.authenticate("random-csrf-value")
    parsed = urlsplit(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert params["client_key"] == ["client-id"]
    assert params["state"] == ["random-csrf-value"]
    assert params["scope"] == ["video.upload"]
    assert params["redirect_uri"] == ["https://example.org/callback"]

def test_exchange_requires_complete_client_configuration(uploader):
    with pytest.raises(ValueError):
        uploader.exchange_code("code")

def test_refresh_requires_existing_refresh_token(uploader):
    with pytest.raises(ValueError):
        uploader.refresh_access_token()

def test_oauth_token_file_roundtrip(tmp_path):
    file = tmp_path / "secrets" / "tiktok.json"
    first = tik.TiktokMediaUploader(token_file=str(file))
    first.access_token = "private-access"
    first.refresh_token = "private-refresh"
    first.save_tokens()
    second = tik.TiktokMediaUploader(token_file=str(file))
    assert second.access_token == "private-access"
    assert second.refresh_token == "private-refresh"
    assert json.loads(file.read_text())["access_token"] == "private-access"

def test_new_oauth_token_file_is_not_world_readable(tmp_path):
    import os
    file = tmp_path / "oauth.json"
    instance = tik.TiktokMediaUploader(token_file=str(file))
    instance.access_token = "secret"
    instance.save_tokens()
    assert file.stat().st_mode & 0o077 == 0

def test_token_exchange_uses_only_expected_oauth_endpoint(uploader, monkeypatch):
    uploader.client_id = "app"
    uploader.client_secret = "private"
    uploader.redirect_uri = "https://example.org/callback"
    calls = []
    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "access_token": "valid", "refresh_token": "refresh"
        })
    monkeypatch.setattr(tik.requests, "post", fake_post)
    uploader.exchange_code("code")
    assert calls[0][0].endswith("/oauth/token/")
    assert calls[0][1]["data"]["grant_type"] == "authorization_code"
    assert uploader.access_token == "valid"

def test_oauth_token_exchange_missing_token_fails(uploader, monkeypatch):
    uploader.client_id = "app"
    uploader.client_secret = "private"
    uploader.redirect_uri = "https://example.org/callback"
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {}
    ))
    with pytest.raises(RuntimeError, match="authorization failed"):
        uploader.exchange_code("code")

def test_refresh_rotates_access_and_persists_refresh_token(uploader, monkeypatch):
    uploader.client_id = "app"
    uploader.client_secret = "secret"
    uploader.refresh_token = "old-refresh"
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {
            "access_token": "new-access", "refresh_token": "new-refresh"
        }
    ))
    uploader.refresh_access_token()
    assert uploader.access_token == "new-access"
    assert uploader.refresh_token == "new-refresh"
    assert json.loads(uploader.token_file.read_text())["refresh_token"] == "new-refresh"

@pytest.mark.parametrize("upload_url", [
    "http://open-upload.tiktokapis.com/video",
    "https://evil.example.com/video",
    "https://open-upload.tiktokapis.com.evil.org/video",
    "https://tiktokapis.com/video",
    "file:///etc/passwd",
])
def test_unexpected_media_transfer_hosts_are_blocked(uploader, monkeypatch, tmp_path, upload_url):
    uploader.access_token = "test-token"
    file = tmp_path / "clip.mp4"
    file.write_bytes(b"sample")
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"error": {"code": "ok"}, "data": {"upload_url": upload_url}}
    ))
    monkeypatch.setattr(tik.requests, "put", lambda *a, **k: pytest.fail("Must not PUT to untrusted host"))
    with pytest.raises(ValueError, match="upload host"):
        uploader.upload_media(str(file))

def test_api_error_blocks_media_upload(uploader, monkeypatch, tmp_path):
    uploader.access_token = "test-token"
    file = tmp_path / "clip.mp4"
    file.write_bytes(b"sample")
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {"error": {"code": "spam_risk"}}
    ))
    with pytest.raises(RuntimeError, match="spam_risk"):
        uploader.upload_media(str(file))

def test_empty_media_is_rejected_before_api_request(uploader, monkeypatch, tmp_path):
    uploader.access_token = "token"
    file = tmp_path / "empty.mp4"
    file.write_bytes(b"")
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: pytest.fail("Should not post"))
    with pytest.raises(ValueError, match="empty"):
        uploader.upload_media(str(file))

@pytest.mark.parametrize("size", [1, 4, 8, 9, 10, 16])
def test_chunked_transfer_has_complete_nonoverlapping_ranges(uploader, monkeypatch, tmp_path, size):
    uploader.access_token = "test-token"
    monkeypatch.setattr(tik, "CHUNK_SIZE", 4)
    file = tmp_path / "clip.mp4"
    file.write_bytes(b"a" * size)
    post = []
    puts = []
    def fake_post(url, **kwargs):
        post.append(kwargs["json"]["source_info"])
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "error": {"code": "ok"}, "data": {
                "upload_url": "https://open-upload.tiktokapis.com/video?id=42",
                "publish_id": "pending-id",
            }
        })
    def fake_put(url, **kwargs):
        puts.append(kwargs)
        return SimpleNamespace(status_code=206, raise_for_status=lambda: None)
    monkeypatch.setattr(tik.requests, "post", fake_post)
    monkeypatch.setattr(tik.requests, "put", fake_put)
    result = uploader.upload_media(str(file))
    assert result == {"publish_id": "pending-id", "status": "pending_creator_confirmation"}
    assert b"".join(put["data"] for put in puts) == b"a" * size
    offsets = [put["headers"]["Content-Range"] for put in puts]
    start = 0
    for put, value in zip(puts, offsets):
        end = start + len(put["data"]) - 1
        assert value == f"bytes {start}-{end}/{size}"
        assert len(put["data"]) <= 4
        start = end + 1
    assert start == size
    assert post[0]["total_chunk_count"] == len(puts)
    assert all(put["headers"]["Content-Type"] == "video/mp4" for put in puts)

def test_chunk_transfer_refuses_unaccepted_response(uploader, monkeypatch, tmp_path):
    uploader.access_token = "token"
    file = tmp_path / "clip.mp4"
    file.write_bytes(b"a" * 8)
    monkeypatch.setattr(tik.requests, "post", lambda *a, **k: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {
            "error": {"code": "ok"}, "data": {
                "upload_url": "https://open-upload.tiktokapis.com/video",
                "publish_id": "pending"
            }
        }
    ))
    monkeypatch.setattr(tik.requests, "put", lambda *a, **k: SimpleNamespace(
        status_code=200, raise_for_status=lambda: None
    ))
    with pytest.raises(RuntimeError, match="not accepted"):
        uploader.upload_media(str(file))
