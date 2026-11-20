import pytest
import shutil
import subprocess

from scripts.editorial_overlays import ass_document, resolve_callouts, validate_callouts


def test_resolves_only_the_unique_phrase_in_its_own_scene(tmp_path):
    srt = tmp_path / "words.srt"
    srt.write_text(
        "1\n00:00:00,250 --> 00:00:00,650\nAyuda\n\n"
        "2\n00:00:02,000 --> 00:00:02,300\nAyuda\n", encoding="utf-8")
    source = "https://example.com/boe"
    cue = {"phrase": "Ayuda", "text": "5.000 €", "source_url": source, "seconds": 3}
    validate_callouts([cue], {source})
    project = {
        "aspect_ratio": "16:9", "word_boundaries": str(srt),
        "voice_metadata": {"alignment_verified": True},
        "sources": [{"url": source}],
        "storyboard": [{"id": "a", "narration": "Ayuda"},
                       {"id": "b", "narration": "Ayuda", "callouts": [cue]}],
    }
    resolved = resolve_callouts(project, 4)
    assert [(x["scene_id"], x["start"], x["end"]) for x in resolved] == [("b", 2., 4.)]
    assert "0:00:02.00,0:00:04.00" in ass_document(resolved)
    assert "5.000 €" in ass_document(resolved)
    project["voice_metadata"]["alignment_verified"] = False
    with pytest.raises(ValueError, match="acoustically verified"):
        resolve_callouts(project, 4)


def test_rejects_unknown_source_and_ass_override():
    source = "https://example.com/source"
    cue = {"phrase": "importe", "text": r"{\pos(0,0)}", "source_url": source, "seconds": 3}
    with pytest.raises(ValueError, match="registered"):
        validate_callouts([cue], set())
    with pytest.raises(ValueError, match="ASS markup"):
        validate_callouts([cue], {source})


def test_rank_uses_editorial_evidence_and_rejects_repeated_events():
    from scripts.editorial_quality import RUBRIC, rank_candidates

    candidate = dict(title="Vivienda", topic="vivienda", repeats_event=False,
                     source_urls=["https://example.com/housing"], exception_reason="",
                     ratings={key: 2 for key in RUBRIC})
    repeated = {**candidate, "title": "Repetido", "repeats_event": True}
    exceptional = {**candidate, "title": "Cine", "topic": "cine"}
    result = rank_candidates([exceptional, repeated, candidate], set())
    assert result["eligible"] == [candidate]
    assert [x["reason"] for x in result["rejected"]] == [
        "unjustified_exception", "published_overlap"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="requires local FFmpeg")
def test_callout_is_burned_into_frames_only_inside_its_window(tmp_path, monkeypatch):
    from PIL import Image
    from scripts.video_assembler import VideoAssembler

    monkeypatch.setenv("VIDEO_RENDER_RESOLUTION", "360p")
    art = tmp_path / "art.png"
    voice = tmp_path / "voice.wav"
    output = tmp_path / "result.mp4"
    Image.new("RGB", (640, 360), (20, 40, 70)).save(art)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "sine=duration=4", str(voice)], check=True)
    VideoAssembler(
        voiceover_file=str(voice), output_file=str(output), media_images=[str(art)],
        scene_motions=["static"], editorial_callouts=[
            {"start": 1, "end": 2.6, "text": "5.000 €"},
        ],
    )._assemble_with_ffmpeg()

    def pixel_at(second):
        path = tmp_path / f"frame-{second}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(second), "-i", str(output),
                        "-frames:v", "1", str(path)], check=True)
        with Image.open(path) as frame:
            return max(frame.convert("RGB").crop((250, 20, 390, 62)).getextrema()[0])

    assert pixel_at(0.8) < 45
    assert pixel_at(1.8) > 175
    assert pixel_at(3.0) < 45
