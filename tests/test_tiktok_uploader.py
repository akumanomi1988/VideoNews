from types import SimpleNamespace

from scripts.Uploaders.tiktok_uploader import TiktokMediaUploader


def test_upload_to_creator_inbox_without_auto_publishing(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "fake-test-token")
    monkeypatch.setenv("TIKTOK_TOKEN_FILE", str(tmp_path / "absent-token.json"))
    file = tmp_path / "sample.mp4"
    file.write_bytes(b"a" * 128)

    calls = []

    def fake_post(url, **kwargs):
        calls.append(("POST", url, kwargs))
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "error": {"code": "ok"},
                "data": {
                    "publish_id": "test-publish-id",
                    "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=1",
                },
            },
        )

    def fake_put(url, **kwargs):
        calls.append(("PUT", url, kwargs))
        return SimpleNamespace(status_code=201, raise_for_status=lambda: None)

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr("requests.put", fake_put)
    result = TiktokMediaUploader().upload_media(str(file))
    assert result["status"] == "pending_creator_confirmation"
    assert result["publish_id"] == "test-publish-id"
    assert [call[0] for call in calls] == ["POST", "PUT"]
    assert calls[1][2]["headers"]["Content-Range"] == "bytes 0-127/128"
