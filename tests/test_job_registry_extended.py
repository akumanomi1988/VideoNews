"""State-machine invariants for local and remotely published news jobs."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from scripts import job_registry as registry

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_JOBS_DB", str(tmp_path / "nested" / "jobs.sqlite3"))

@pytest.mark.parametrize("url,format", [
    ("", "short"), ("", "long"), ("https://example.com/story", ""),
    ("https://example.com/story", "SHORT"), ("https://example.com/story", "vertical"),
])
def test_invalid_reservations_are_rejected(url, format):
    with pytest.raises(ValueError):
        registry.claim(url, format)

def test_unknown_story_has_no_history():
    assert registry.get("https://example.org/missing") is None
    assert registry.review_required() == []

def test_claim_records_format_timestamps_and_stable_id():
    url = "https://example.org/story"
    job_id = registry.claim(url, "long")
    row = registry.get(url)
    assert row["job_id"] == job_id
    assert row["format"] == "long"
    assert row["state"] == "RESERVED"
    assert row["created_at"] <= row["updated_at"]
    assert row["output"] is None

@pytest.mark.parametrize("next_state", ["PREPARING", "UPLOADING"])
def test_claim_can_advance_to_supported_milestone(next_state):
    url = "https://example.org/advance"
    job = registry.claim(url, "short")
    registry.advance(job, next_state)
    assert registry.get(url)["state"] == next_state

@pytest.mark.parametrize("illegal", ["PUBLISHED", "RETRYING", "FAILED", "", "COMPLETED"])
def test_unrecognized_milestones_are_rejected(illegal):
    job = registry.claim("https://example.org/check", "short")
    with pytest.raises(ValueError):
        registry.advance(job, illegal)
    assert registry.get("https://example.org/check")["state"] == "RESERVED"

def test_cannot_advance_completed_work():
    url = "https://example.org/final"
    job = registry.claim(url, "short")
    registry.complete(job, "saved.mp4")
    with pytest.raises(RuntimeError):
        registry.advance(job, "UPLOADING")
    assert registry.get(url)["state"] == "COMPLETED"

def test_missing_output_does_not_complete_job():
    url = "https://example.org/output"
    job = registry.claim(url, "short")
    with pytest.raises(ValueError):
        registry.complete(job, "")
    assert registry.get(url)["state"] == "RESERVED"

def test_unknown_job_cannot_be_completed():
    with pytest.raises(RuntimeError):
        registry.complete("nonexistent", "clip.mp4")

def test_failure_before_upload_has_bounded_error():
    url = "https://example.org/error"
    job = registry.claim(url, "short")
    registry.fail(job, "E" * 2000)
    row = registry.get(url)
    assert row["state"] == "FAILED"
    assert len(row["last_error"]) == 1500
    assert registry.review_required() == []

def test_failed_job_retries_with_fresh_id_and_cleared_error():
    url = "https://example.org/retry"
    first = registry.claim(url, "short")
    registry.fail(first, "temporary")
    second = registry.claim(url, "long")
    row = registry.get(url)
    assert second != first
    assert row["format"] == "long"
    assert row["last_error"] is None
    assert row["state"] == "RESERVED"
    with pytest.raises(RuntimeError):
        registry.complete(first, "stale.mp4")

@pytest.mark.parametrize("state", ["RESERVED", "PREPARING", "UPLOADING", "NEEDS_REVIEW", "COMPLETED"])
def test_unresolved_or_finished_story_never_gets_duplicate_claim(state):
    url = "https://example.org/one"
    job = registry.claim(url, "short")
    if state == "PREPARING":
        registry.advance(job, "PREPARING")
    elif state in ("UPLOADING", "NEEDS_REVIEW"):
        registry.advance(job, "UPLOADING")
        if state == "NEEDS_REVIEW":
            registry.fail(job, "ambiguous")
    elif state == "COMPLETED":
        registry.complete(job, "clip.mp4")
    with pytest.raises(registry.DuplicateJobError):
        registry.claim(url, "long")

@pytest.mark.parametrize("state", ["RESERVED", "PREPARING", "UPLOADING"])
def test_pending_review_lists_only_nonterminal_states(state):
    url = "https://example.org/pending"
    job = registry.claim(url, "short")
    if state != "RESERVED":
        registry.advance(job, state)
    items = registry.review_required()
    assert [(item["source_url"], item["state"]) for item in items] == [(url, state)]

def test_operator_cannot_claim_publication_without_reference():
    url = "https://example.org/uncertain"
    job = registry.claim(url, "short")
    registry.advance(job, "UPLOADING")
    registry.fail(job, "timeout")
    with pytest.raises(ValueError):
        registry.reconcile(url, published=True)
    assert registry.get(url)["state"] == "NEEDS_REVIEW"

def test_operator_cannot_resolve_unknown_or_already_finished_job():
    with pytest.raises(ValueError):
        registry.reconcile("https://example.org/missing", published=False)
    url = "https://example.org/finished"
    job = registry.claim(url, "short")
    registry.complete(job, "video.mp4")
    with pytest.raises(ValueError):
        registry.reconcile(url, published=False)

def test_reconciled_remote_reference_is_saved():
    url = "https://example.org/remotely-finished"
    job = registry.claim(url, "long")
    registry.advance(job, "UPLOADING")
    registry.fail(job, "connection reset")
    registry.reconcile(url, published=True, reference="https://youtu.be/confirmed")
    row = registry.get(url)
    assert row["output"] == "https://youtu.be/confirmed"
    assert row["last_error"] is None
    assert row["state"] == "COMPLETED"

def test_manual_negative_reconciliation_is_explicitly_retryable():
    url = "https://example.org/no-upload"
    job = registry.claim(url, "short")
    registry.advance(job, "UPLOADING")
    registry.fail(job, "indeterminate")
    registry.reconcile(url, published=False)
    assert registry.get(url)["state"] == "FAILED"
    assert registry.claim(url, "short") != job

def test_registry_persists_after_reopening_database():
    url = "https://example.org/persistent"
    job = registry.claim(url, "long")
    with registry._connection() as db:
        assert db.execute("SELECT job_id FROM article_jobs WHERE source_url=?", (url,)).fetchone()[0] == job
    assert registry.get(url)["job_id"] == job

def test_sql_injection_looking_url_is_treated_as_an_exact_key():
    url = "https://example.org/'; DROP TABLE article_jobs;--"
    job = registry.claim(url, "short")
    assert registry.get(url)["job_id"] == job
    assert registry.claim("https://example.org/normal", "long")

def test_distinct_stories_can_reserve_in_parallel():
    urls = [f"https://example.org/item-{i}" for i in range(16)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda url: registry.claim(url, "short"), urls))
    assert len(set(ids)) == len(urls)
    assert len(registry.review_required()) == len(urls)
