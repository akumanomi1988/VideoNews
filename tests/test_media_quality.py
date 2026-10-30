"""Exercise acceptance against real decoded media, including negative cases."""
import shutil
import subprocess

import pytest

from scripts.media_quality import inspect_streams


@pytest.mark.parametrize("size", ["180x320", "320x180"])
def test_real_decode_accepts_both_orientations_and_rejects_silence(tmp_path, size):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required")
    for silent in (False, True):
        video = tmp_path / f"sample-{silent}.mp4"
        audio = "anullsrc=r=48000:cl=mono" if silent else "sine=frequency=440:sample_rate=48000"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        f"testsrc2=size={size}:rate=24", "-f", "lavfi", "-i", audio,
                        "-t", "2", "-af", "volume=1.5", "-c:v", "libx264", "-c:a", "aac",
                        str(video)], check=True, capture_output=True)
        report = inspect_streams(video, 2)
        assert report["decode_ok"]
        assert bool(report["issues"]) == silent


def test_real_decode_rejects_prolonged_black_video(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required")
    video = tmp_path / "black.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:size=180x320:rate=24", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=48000", "-t", "2", "-c:v", "libx264",
                    "-c:a", "aac", str(video)], check=True, capture_output=True)
    assert "Unexpected black interval inside the video" in inspect_streams(video, 2)["issues"]
