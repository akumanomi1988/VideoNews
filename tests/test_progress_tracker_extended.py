"""Progress reporting is stable, bounded and serializable."""
import json
from pathlib import Path
import pytest
from scripts.utils.progress_tracker import ProgressTracker, StageStatus

def test_all_expected_stages_start_pending():
    report = ProgressTracker().get_progress_report()
    assert set(report["stages"]) == {
        "article_processing", "media_generation", "audio_generation",
        "subtitle_generation", "video_assembly", "upload"
    }
    assert all(s["status"] == "PENDING" for s in report["stages"].values())
    assert report["total_progress"] == 0

@pytest.mark.parametrize("unknown", ["unknown", "voiceover", ""])
def test_unknown_stage_cannot_be_started(unknown):
    with pytest.raises(ValueError):
        ProgressTracker().start_stage(unknown)

@pytest.mark.parametrize("requested,expected", [
    (-40, 0), (0, 0), (15, 15), (100, 100), (200, 100)
])
def test_progress_values_are_clamped(requested, expected):
    tracker = ProgressTracker()
    tracker.start_stage("media_generation")
    tracker.update_progress(requested)
    assert tracker.get_progress_report()["stages"]["media_generation"]["progress"] == expected

def test_completing_stage_is_recorded_with_timing_and_metadata():
    tracker = ProgressTracker()
    tracker.start_stage("article_processing", "extracting")
    tracker.complete_stage({"title": "Report"})
    state = tracker.get_progress_report()
    assert state["total_progress"] == pytest.approx(10.0)
    assert state["stages"]["article_processing"]["status"] == "COMPLETED"
    assert state["stages"]["article_processing"]["metadata"]["title"] == "Report"
    assert state["stages"]["article_processing"]["duration"] >= 0

def test_in_progress_stage_uses_weighted_percentage():
    tracker = ProgressTracker()
    tracker.start_stage("media_generation")
    tracker.update_progress(50)
    assert tracker.get_progress_report()["total_progress"] == pytest.approx(15)

def test_skipped_stage_counts_as_complete_progress():
    tracker = ProgressTracker()
    tracker.start_stage("subtitle_generation")
    tracker.skip_stage("not required")
    assert tracker.get_progress_report()["total_progress"] == pytest.approx(10)
    assert tracker.get_progress_report()["stages"]["subtitle_generation"]["status"] == "SKIPPED"

def test_failed_stage_records_error_without_fake_completion():
    tracker = ProgressTracker()
    tracker.start_stage("upload")
    tracker.fail_stage("quota exhausted", {"provider": "youtube"})
    record = tracker.get_progress_report()["stages"]["upload"]
    assert record["status"] == "FAILED"
    assert record["error"] == "quota exhausted"
    assert record["metadata"]["provider"] == "youtube"
    assert tracker.get_progress_report()["total_progress"] == 0

def test_callback_receives_progress_events():
    calls = []
    tracker = ProgressTracker(callback=calls.append)
    tracker.start_stage("audio_generation")
    tracker.update_progress(70, "voicing")
    tracker.complete_stage()
    assert len(calls) == 3
    assert calls[1]["stages"]["audio_generation"]["message"] == "voicing"
    assert calls[-1]["stages"]["audio_generation"]["status"] == "COMPLETED"

def test_callback_exception_does_not_abort_processing():
    def broken(_):
        raise RuntimeError("websocket offline")
    tracker = ProgressTracker(callback=broken)
    tracker.start_stage("article_processing")
    tracker.complete_stage()
    assert tracker.stages["article_processing"].status == StageStatus.COMPLETED

def test_update_without_current_stage_is_safe():
    tracker = ProgressTracker()
    tracker.update_progress(70)
    tracker.complete_stage()
    tracker.fail_stage("ignored")
    tracker.skip_stage("ignored")
    assert tracker.get_progress_report()["total_progress"] == 0

def test_report_can_be_saved_as_parseable_json(tmp_path):
    tracker = ProgressTracker()
    tracker.start_stage("article_processing")
    tracker.complete_stage()
    destination = tmp_path / "progress.json"
    tracker.save_report(str(destination))
    report = json.loads(destination.read_text())
    assert report["stages"]["article_processing"]["status"] == "COMPLETED"

def test_reset_clears_previous_state():
    tracker = ProgressTracker()
    tracker.start_stage("upload")
    tracker.fail_stage("oops")
    tracker.reset()
    assert tracker.current_stage is None
    assert tracker.get_progress_report()["total_progress"] == 0
    assert all(s["status"] == "PENDING" for s in tracker.get_progress_report()["stages"].values())
