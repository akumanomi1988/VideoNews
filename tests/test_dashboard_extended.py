"""Dashboard metrics and health checks against a temporary metrics directory."""
import json
import time
from pathlib import Path
import pytest
from scripts import dashboard

@pytest.fixture
def client(tmp_path):
    folder = tmp_path / "metrics"
    folder.mkdir()
    api = dashboard.create_app(str(folder))
    api.testing = True
    return api.test_client(), folder

def _metric(folder, name, *, success=False, failed=False, duration=0, hours_old=0):
    import os
    path = folder / f"{name}.json"
    path.write_text(json.dumps({
        "pipeline_id": name, "start_time": time.time() - hours_old * 3600,
        "duration": duration, "is_completed": success, "is_failed": failed
    }), encoding="utf-8")
    if hours_old:
        then = time.time() - hours_old * 3600
        os.utime(path, (then, then))

def test_dashboard_index_renders_valid_html(client):
    web, folder = client
    response = web.get("/")
    assert response.status_code == 200
    assert b"Pipeline Dashboard" in response.data

def test_empty_summary_contains_zeroes(client):
    web, folder = client
    summary = web.get("/api/metrics/summary").get_json()
    assert summary["total_pipelines"] == 0
    assert summary["active_pipelines"] == 0

def test_completed_failed_and_running_jobs_counted_once(client):
    web, folder = client
    _metric(folder, "done", success=True, duration=12)
    _metric(folder, "fail", failed=True, duration=4)
    _metric(folder, "active")
    summary = web.get("/api/metrics/summary").get_json()
    assert summary["total_pipelines"] == 3
    assert summary["completed_pipelines"] == 1
    assert summary["failed_pipelines"] == 1
    assert summary["active_pipelines"] == 1
    assert summary["average_duration"] == 12

def test_recent_endpoint_orders_newest_first(client):
    web, folder = client
    _metric(folder, "new", success=True)
    _metric(folder, "old", success=True, hours_old=2)
    ids = [row["pipeline_id"] for row in web.get("/api/metrics/recent").get_json()]
    assert ids == ["new", "old"]

def test_old_metrics_do_not_inflate_24_hour_totals(client):
    web, folder = client
    _metric(folder, "recent", success=True)
    _metric(folder, "expired", success=True, hours_old=30)
    assert web.get("/api/metrics/summary").get_json()["total_pipelines"] == 1

def test_single_pipeline_lookup_by_id(client):
    web, folder = client
    _metric(folder, "specific", failed=True)
    record = web.get("/api/metrics/pipeline/specific").get_json()
    assert record["pipeline_id"] == "specific"
    assert record["is_failed"] is True

def test_nonexistent_pipeline_returns_empty_object(client):
    web, folder = client
    assert web.get("/api/metrics/pipeline/missing").get_json() == {}

def test_corrupt_metric_json_does_not_take_down_dashboard(client):
    web, folder = client
    (folder / "bad.json").write_text("{broken", encoding="utf-8")
    assert web.get("/api/metrics/summary").status_code == 200
    assert web.get("/api/metrics/active").get_json() == []

def test_active_endpoint_filters_terminal_jobs(client):
    web, folder = client
    _metric(folder, "active")
    _metric(folder, "done", success=True)
    _metric(folder, "failed", failed=True)
    assert [m["pipeline_id"] for m in web.get("/api/metrics/active").get_json()] == ["active"]
