"""Lightweight behavior checks; no live tokens or network calls are required."""

import json
from types import SimpleNamespace
import pytest
from bot.security import admin_user_ids, is_authorized
from scripts.runtime_config import load_runtime_config
from scripts.services.local_uploader import LocalVideoUploader
from scripts.interfaces import VideoMetadata


def test_admin_ids_fail_closed():
    assert admin_user_ids('') == frozenset()
    assert admin_user_ids('12345, 67890') == frozenset({12345, 67890})
    with pytest.raises(ValueError):
        admin_user_ids('someone')
    with pytest.raises(ValueError):
        admin_user_ids('-1')


def test_authorization_requires_private_chat_and_matching_user():
    update = SimpleNamespace(effective_user=SimpleNamespace(id=12345),
                             effective_chat=SimpleNamespace(id=12345, type='private'))
    assert is_authorized(update, frozenset({12345}))
    assert not is_authorized(update, frozenset())
    assert not is_authorized(update, frozenset({999}))
    update.effective_chat.type = 'group'
    assert not is_authorized(update, frozenset({12345}))


def test_runtime_config_environment_overrides_without_file_changes(tmp_path, monkeypatch):
    config_path = tmp_path / 'settings.json'
    config_path.write_text(json.dumps({'settings': {'temp_dir': 'tmp'},
                                       'serpapi': {'api_key': ''}}), encoding='utf-8')
    monkeypatch.setenv('SERPAPI_API_KEY', 'secret-only-in-memory')
    monkeypatch.delenv('YOUTUBE_UPLOAD_ENABLED', raising=False)
    loaded = load_runtime_config(str(config_path))
    assert loaded['serpapi']['api_key'] == 'secret-only-in-memory'
    assert loaded['upload_type'] == 'local'
    assert 'secret-only-in-memory' not in config_path.read_text(encoding='utf-8')


def test_youtube_requires_explicit_opt_in(tmp_path, monkeypatch):
    config_path = tmp_path / 'settings.json'
    config_path.write_text('{}', encoding='utf-8')
    monkeypatch.setenv('YOUTUBE_UPLOAD_ENABLED', 'true')
    assert load_runtime_config(str(config_path))['upload_type'] == 'youtube'


def test_local_uploader_preserves_video_and_metadata(tmp_path):
    video = tmp_path / 'source.mp4'
    video.write_bytes(b'fake video for storage test')
    meta = VideoMetadata(title='Example', description='Description',
                         tags=['news'], thumbnail_path='')
    dest = LocalVideoUploader(str(tmp_path / 'published')).upload(str(video), meta)
    from pathlib import Path
    final = Path(dest)
    assert final.read_bytes() == video.read_bytes()
    assert json.loads(final.with_suffix('.json').read_text(encoding='utf-8'))['title'] == 'Example'
