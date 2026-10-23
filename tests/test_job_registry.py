"""Transactional retries and publication ambiguity: no duplicated videos."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts import job_registry as jobs


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_JOBS_DB", str(tmp_path / "jobs.sqlite3"))


def test_only_one_concurrent_claim_succeeds():
    def claim_attempt(_):
        try:
            return jobs.claim("https://example.org/first-story", "short")
        except jobs.DuplicateJobError:
            return None

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(claim_attempt, range(24)))
    assert len([x for x in results if x is not None]) == 1
    assert jobs.get("https://example.org/first-story")["state"] == "RESERVED"


def test_pre_upload_failure_is_safe_to_retry():
    url = "https://example.org/retryable"
    first = jobs.claim(url, "short")
    jobs.advance(first, "PREPARING")
    jobs.fail(first, "Speech service temporarily unavailable")
    assert jobs.get(url)["state"] == "FAILED"
    second = jobs.claim(url, "short")
    assert first != second
    jobs.complete(second, "/output/clip.mp4")
    assert jobs.get(url)["state"] == "COMPLETED"
    with pytest.raises(jobs.DuplicateJobError):
        jobs.claim(url, "short")


def test_uncertain_upload_blocks_automatic_retry():
    url = "https://example.org/upload"
    first = jobs.claim(url, "long")
    jobs.advance(first, "PREPARING")
    jobs.advance(first, "UPLOADING")
    jobs.fail(first, "Connection dropped after upload started")
    assert jobs.get(url)["state"] == "NEEDS_REVIEW"
    assert len(jobs.review_required()) == 1
    with pytest.raises(jobs.DuplicateJobError):
        jobs.claim(url, "long")


def test_completed_upload_is_not_reset_on_later_error():
    url = "https://example.org/already-done"
    job_id = jobs.claim(url, "short")
    jobs.advance(job_id, "UPLOADING")
    jobs.complete(job_id, "https://www.youtube.com/watch?v=example")
    jobs.fail(job_id, "Telegram delivery failed")
    assert jobs.get(url)["state"] == "COMPLETED"
