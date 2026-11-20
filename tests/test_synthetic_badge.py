"""Verify that the renderer leaves the lower-left artwork unobstructed."""
import shutil
import subprocess

import pytest
from PIL import Image

from scripts.video_assembler import VideoAssembler


@pytest.mark.parametrize("aspect", ["16:9", "9:16"])
def test_render_does_not_overlay_an_ai_badge(tmp_path, monkeypatch, aspect):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required")
    monkeypatch.setenv("VIDEO_RENDER_RESOLUTION", "360p")
    dimensions = (640, 360) if aspect == "16:9" else (360, 640)
    paths = []
    for name, color in (("synthetic", "red"), ("original", "blue")):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", dimensions, color).save(path)
        paths.append(str(path))
    voice = tmp_path / "voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=4", str(voice)], check=True)
    output = tmp_path / "clean.mp4"
    assembler = VideoAssembler(voiceover_file=str(voice), output_file=str(output),
                               media_images=paths, aspect_ratio=aspect, image_durations=[2, 2],
                               scene_motions=["static", "static"], synthetic_scene_flags=[True, False])
    assembler._assemble_with_ffmpeg()
    width, height = dimensions
    diameter = max(22, round(width / 30))
    left = round(width * 0.028)
    top = height - round(height * (0.12 if aspect == "9:16" else 0.06)) - diameter
    for second in (1, 2.15, 3.2):
        frame = tmp_path / f"frame-{second}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(second), "-i", str(output),
                        "-frames:v", "1", str(frame)], check=True)
        with Image.open(frame) as image:
            frame = image.convert("RGB")
            reference = frame.getpixel((width // 2, top + diameter // 2))
            pixels = frame.crop((left, top, left + diameter, top + diameter)).getdata()
            assert max(abs(value - expected)
                       for pixel in pixels for value, expected in zip(pixel, reference)) <= 3
    assert not list(tmp_path.glob("_ia_badge_*.png"))
