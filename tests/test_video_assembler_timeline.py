from scripts.video_assembler import VideoAssembler


def test_real_ffmpeg_preserves_geometry_and_explicit_display_aspect(tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess

    import pytest
    from PIL import Image, ImageDraw

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required")
    monkeypatch.setenv("VIDEO_RENDER_RESOLUTION", "360p")
    image = tmp_path / "circle.png"
    canvas = Image.new("RGB", (640, 640), "navy")
    ImageDraw.Draw(canvas).ellipse((230, 230, 410, 410), fill="red")
    canvas.save(image)
    audio = tmp_path / "voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=2", str(audio)], check=True)
    for aspect, dimensions in (("16:9", (640, 360)), ("9:16", (360, 640))):
        video = tmp_path / f"video-{dimensions[0]}.mp4"
        assembler = VideoAssembler(voiceover_file=str(audio), output_file=str(video),
                                   media_images=[str(image)], aspect_ratio=aspect,
                                   scene_motions=["static"])
        assembler.assemble_video()
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json", str(video)]))
        stream = probe["streams"][0]
        assert (stream["width"], stream["height"]) == dimensions
        assert stream["sample_aspect_ratio"] == "1:1"
        assert stream["display_aspect_ratio"] == aspect
        frame = tmp_path / f"frame-{dimensions[0]}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(video),
                        "-frames:v", "1", str(frame)], check=True)
        decoded = Image.open(frame).convert("RGB")
        points = [(x, y) for y in range(decoded.height) for x in range(decoded.width)
                  if decoded.getpixel((x, y))[0] > 150 and decoded.getpixel((x, y))[1] < 80]
        width = max(x for x, y in points) - min(x for x, y in points)
        height = max(y for x, y in points) - min(y for x, y in points)
        assert abs(width / height - 1) < 0.04, "The circular subject was stretched"


def test_scene_frame_counts_follow_voice_duration():
    assert VideoAssembler._allocate_frame_counts([1.0, 2.0, 1.0], 96) == [24, 48, 24]


def test_scene_frame_counts_cover_output_exactly():
    counts = VideoAssembler._allocate_frame_counts([0.15, 0.35, 0.5], 101)
    assert len(counts) == 3
    assert sum(counts) == 101
    assert all(count > 0 for count in counts)


def test_real_scene_transition_starts_at_its_narration_boundary(tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess

    import pytest
    from PIL import Image

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required")
    monkeypatch.setenv("VIDEO_RENDER_RESOLUTION", "360p")
    images = []
    for name, color in (("first", "red"), ("second", "blue")):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", (640, 360), color).save(path)
        images.append(str(path))
    audio = tmp_path / "voice.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=4", str(audio)], check=True)
    output = tmp_path / "timed.mp4"
    VideoAssembler(voiceover_file=str(audio), output_file=str(output), media_images=images,
                   aspect_ratio="16:9", image_durations=[0.7, 3.3],
                   scene_motions=["static", "static"], scene_transitions=["crossfade", "crossfade"]).assemble_video()
    frame = tmp_path / "before-transition.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.6", "-i", str(output),
                    "-frames:v", "1", str(frame)], check=True)
    with Image.open(frame) as image:
        red, green, blue = image.convert("RGB").getpixel((320, 180))
    assert red > 220 and blue < 30, "Next scene appeared before its narration boundary"
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(output)]))
    assert abs(float(probe["format"]["duration"]) - 4) < 0.05
