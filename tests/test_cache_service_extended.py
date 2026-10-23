"""Durable content-addressed cache behaviors and corruption resilience."""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from scripts.services.cache_service import CacheManager

@pytest.fixture
def cache(tmp_path):
    return CacheManager(str(tmp_path / "cache"), max_age_days=7)

def _source(tmp_path, name="image.png", data=b"test-image"):
    p = tmp_path / name
    p.write_bytes(data)
    return p

def test_cache_miss_returns_none(cache):
    assert cache.get("does-not-exist") is None

def test_cache_roundtrip_preserves_bytes_and_extension(cache, tmp_path):
    src = _source(tmp_path)
    path = Path(cache.put("image prompt", str(src), {"orientation": "portrait"}))
    assert path.read_bytes() == src.read_bytes()
    assert path.suffix == ".png"
    assert cache.get("image prompt", {"orientation": "portrait"}) == str(path)

def test_same_key_different_parameters_does_not_collide(cache, tmp_path):
    src = _source(tmp_path)
    portrait = cache.put("same prompt", str(src), {"orientation": "portrait"})
    landscape = cache.put("same prompt", str(src), {"orientation": "landscape"})
    assert portrait != landscape
    assert len(cache.metadata) == 2

def test_cache_metadata_persists_across_instances(cache, tmp_path):
    src = _source(tmp_path)
    saved = cache.put("persistent", str(src))
    reopened = CacheManager(str(cache.cache_dir))
    assert reopened.get("persistent") == saved

def test_deleted_source_does_not_invalidate_cached_copy(cache, tmp_path):
    src = _source(tmp_path)
    cached = cache.put("save-copy", str(src))
    src.unlink()
    assert Path(cached).is_file()
    assert cache.get("save-copy") == cached

def test_missing_cached_file_is_evicted_from_metadata(cache, tmp_path):
    src = _source(tmp_path)
    Path(cache.put("missing-file", str(src))).unlink()
    assert cache.get("missing-file") is None
    assert len(cache.metadata) == 0

def test_expired_cache_file_is_rejected_and_deleted(cache, tmp_path):
    src = _source(tmp_path)
    cached = Path(cache.put("expired", str(src)))
    key = next(iter(cache.metadata))
    cache.metadata[key]["created"] = (datetime.now() - timedelta(days=10)).timestamp()
    assert cache.get("expired") is None
    assert not cached.exists()

def test_corrupted_metadata_is_treated_as_empty(tmp_path):
    root = tmp_path / "cache"
    root.mkdir()
    (root / "cache_metadata.json").write_text("{invalid", encoding="utf-8")
    cache = CacheManager(str(root))
    assert cache.get("x") is None

def test_cache_statistics_measure_actual_assets(cache, tmp_path):
    src = _source(tmp_path, data=b"0123456789")
    cache.put("s1", str(src))
    stats = cache.get_stats()
    assert stats["total_files"] == 1
    assert stats["total_size_mb"] == pytest.approx(10 / 1024 / 1024)

def test_expired_cleanup_preserves_fresh_entries(cache, tmp_path):
    src = _source(tmp_path)
    old = cache.put("old", str(src))
    fresh = cache.put("new", str(src))
    key = cache._compute_hash("old")
    cache.metadata[key]["created"] = (datetime.now() - timedelta(days=15)).timestamp()
    cache.cleanup()
    assert not Path(old).exists()
    assert Path(fresh).exists()

def test_orphaned_cache_artifact_is_removed(cache):
    orphan = cache.cache_dir / "orphan.png"
    orphan.write_bytes(b"orphan")
    cache.cleanup()
    assert not orphan.exists()
    assert cache.metadata_file.exists() is False or cache.metadata_file.is_file()

def test_clear_removes_assets_and_resets_index(cache, tmp_path):
    src = _source(tmp_path)
    saved = cache.put("to-clear", str(src))
    cache.clear()
    assert not Path(saved).exists()
    assert cache.get("to-clear") is None
    assert cache.get_stats()["total_files"] == 0

def test_stale_cache_index_does_not_revalidate_nonexistent_asset(cache, tmp_path):
    src = _source(tmp_path)
    cached = Path(cache.put("disappeared", str(src)))
    cached.unlink()
    new_instance = CacheManager(str(cache.cache_dir))
    assert new_instance.get("disappeared") is None
