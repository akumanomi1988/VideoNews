"""Full-stream technical acceptance checks; semantic review remains editorial."""
import json
import os
import re
import subprocess
from fractions import Fraction


def inspect_streams(video, duration):
    """Decode every frame and measure true peak, loudness and black intervals."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-xerror", "-i", str(video),
         "-vf", "blackdetect=d=0.12:pix_th=0.02:pic_th=0.99",
         "-af", "ebur128=peak=true", "-f", "null", os.devnull],
        capture_output=True, text=True, timeout=min(900, max(120, duration * 3)))
    issues = []
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)],
                           capture_output=True, text=True, timeout=30)
    streams = json.loads(probe.stdout).get("streams", []) if probe.returncode == 0 else []
    picture = next((item for item in streams if item.get("codec_type") == "video"), {})
    sound = next((item for item in streams if item.get("codec_type") == "audio"), {})
    fps = float(Fraction(picture.get("avg_frame_rate", "0/1")))
    av_drift = abs(float(picture.get("duration", duration)) - float(sound.get("duration", 0)))
    pixel_aspect = picture.get("sample_aspect_ratio")
    if pixel_aspect and pixel_aspect != "1:1":
        issues.append("Video pixels must have a square sample aspect ratio (1:1)")
    if picture.get("pix_fmt") != "yuv420p":
        issues.append("Video pixel format must be yuv420p")
    if not 24 <= fps <= 60:
        issues.append("Video frame rate must be between 24 and 60 FPS")
    if av_drift > 0.15:
        issues.append("Audio/video stream duration drift exceeds 150 ms")
    if result.returncode:
        issues.append("Full audiovisual decode failed")
    intervals = [dict(zip(("start", "end", "duration"), map(float, values)))
                 for values in re.findall(
                     r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", result.stderr)]
    # Deliberate opening/closing fades are allowed; internal black gaps are not.
    internal = [item for item in intervals if item["duration"] > 1.2 or
                (item["start"] > 0.6 and item["end"] < duration - 0.6)]
    if internal:
        issues.append("Unexpected black interval inside the video")
    loudness = re.findall(r"I:\s*(-?[\d.]+) LUFS", result.stderr)
    peaks = re.findall(r"Peak:\s*(-?[\d.]+) dBFS", result.stderr)
    integrated = float(loudness[-1]) if loudness else None
    peak = float(peaks[-1]) if peaks else None
    if integrated is None or not -24 <= integrated <= -10:
        issues.append("Integrated audio loudness must be between -24 and -10 LUFS")
    if peak is None or peak > -0.5:
        issues.append("Audio true peak must stay at or below -0.5 dBTP")
    return {"method": "complete FFmpeg frame/audio decode", "decode_ok": result.returncode == 0,
            "width": picture.get("width"), "height": picture.get("height"), "fps": fps,
            "sample_aspect_ratio": pixel_aspect,
            "display_aspect_ratio": picture.get("display_aspect_ratio"),
            "pixel_format": picture.get("pix_fmt"), "av_duration_drift_seconds": av_drift,
            "integrated_lufs": integrated, "true_peak_dbtp": peak,
            "black_intervals": intervals, "issues": issues}
