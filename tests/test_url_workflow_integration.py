"""Real VideoService orchestration with deterministic external stubs.

The full production Python dependency set is required. The service and
transactional SQLite registry are NOT mocked; only remote APIs and encoder
output from individual providers are replaced.
"""
import asyncio
import threading
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def private_job_db(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_JOBS_DB", str(tmp_path / "jobs.sqlite3"))


def _stub_service(monkeypatch, tmp_path, *, upload=False, first_failure=False):
    from bot.services import video_service as video
    from scripts import job_registry as jobs

    starts = []
    monkeypatch.setattr(video, "validate_public_url", lambda url: None)
    monkeypatch.setattr(video, "is_url_processed", lambda url: False)
    monkeypatch.setattr(video, "save_processed_news", lambda data: None)

    class Article:
        title = "Verified synthetic article"
        text = "A deterministic synthetic story with enough text for production flow checks."

    class Extractor:
        def extract_article(self, url):
            return Article()

    class Processor:
        def __init__(self, config_file=None):
            self.on_publish_start = None

        def process_latest_news_in_short_format(self, topic):
            starts.append(topic["url"])
            if first_failure and len(starts) == 1:
                return None
            if upload:
                self.on_publish_start()
                raise OSError("Socket disconnected during upload")
            destination = tmp_path / "video.mp4"
            destination.write_bytes(b"mock video output: actual encoding tested separately")
            return {"local_path": str(destination)}

        process_latest_news_in_long_format = process_latest_news_in_short_format

    monkeypatch.setattr(video, "NewsExtractor", Extractor)
    monkeypatch.setattr(video, "NewsVideoProcessor", Processor)
    return video.VideoService(), jobs, starts


def test_article_processed_only_once(tmp_path, monkeypatch):
    service, jobs, starts = _stub_service(monkeypatch, tmp_path)
    url = "https://example.org/atomic"
    result = asyncio.run(service.process_url_short(url))
    assert Path(result).is_file()
    assert jobs.get(url)["state"] == "COMPLETED"
    with pytest.raises(jobs.DuplicateJobError):
        asyncio.run(service.process_url_short(url))
    assert starts == [url]


def test_failure_before_upload_allows_retry(tmp_path, monkeypatch):
    service, jobs, starts = _stub_service(monkeypatch, tmp_path, first_failure=True)
    url = "https://example.org/retry"
    with pytest.raises(RuntimeError, match="did not return"):
        asyncio.run(service.process_url_short(url))
    assert jobs.get(url)["state"] == "FAILED"
    assert Path(asyncio.run(service.process_url_short(url))).is_file()
    assert starts == [url, url]


def test_ambiguous_upload_failure_never_reposts(tmp_path, monkeypatch):
    service, jobs, starts = _stub_service(monkeypatch, tmp_path, upload=True)
    url = "https://example.org/publishing"
    with pytest.raises(OSError, match="disconnected"):
        asyncio.run(service.process_url_short(url))
    assert jobs.get(url)["state"] == "NEEDS_REVIEW"
    with pytest.raises(jobs.DuplicateJobError):
        asyncio.run(service.process_url_short(url))
    assert starts == [url]


def test_concurrent_requests_share_exactly_one_claim(tmp_path, monkeypatch):
    service, jobs, starts = _stub_service(monkeypatch, tmp_path)
    url = "https://example.org/parallel"

    async def submit_both():
        return await asyncio.gather(
            service.process_url_short(url),
            service.process_url_short(url),
            return_exceptions=True,
        )

    outcomes = asyncio.run(submit_both())
    assert len(starts) == 1
    assert len([x for x in outcomes if isinstance(x, str)]) == 1
    assert len([x for x in outcomes if isinstance(x, jobs.DuplicateJobError)]) == 1
