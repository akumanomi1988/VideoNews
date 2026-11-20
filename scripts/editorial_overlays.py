"""Compile sourced storyboard callouts to the existing libass render path."""
import re


def words(text):
    return re.findall(r"[^\W_]+", text.casefold())


def validate_callouts(cues, source_urls):
    if not isinstance(cues, list) or len(cues) > 12:
        raise ValueError("callouts must be a list of up to 12 events per scene")
    for cue in cues:
        if not isinstance(cue, dict) or set(cue) != {"phrase", "text", "source_url", "seconds"}:
            raise ValueError("callouts require phrase, text, source_url and seconds")
        if not isinstance(cue["source_url"], str) or cue["source_url"] not in source_urls:
            raise ValueError("callout source must be registered in the project")
        if not isinstance(cue["phrase"], str) or not words(cue["phrase"]) or len(cue["phrase"]) > 160:
            raise ValueError("callout requires a short, exact spoken phrase")
        label = cue["text"]
        if (not isinstance(label, str) or not label.strip() or len(label) > 48
                or any(c in "{}\\" or ord(c) < 32 for c in label)):
            raise ValueError("callout text must be 1–48 printable characters without ASS markup")
        if type(cue["seconds"]) not in (int, float) or not 1 <= cue["seconds"] <= 12:
            raise ValueError("callout seconds must be between 1 and 12")


def resolve_callouts(project, duration):
    scenes = project.get("storyboard", [])
    if not any(scene.get("callouts") for scene in scenes):
        return []
    if project.get("aspect_ratio") != "16:9":
        raise ValueError("editorial callouts currently require landscape layout")
    if not project.get("voice_metadata", {}).get("alignment_verified"):
        raise ValueError("editorial callouts require acoustically verified narration")
    from scripts.MediaManagers.SRT_Processor import SRTProcessor

    entries = SRTProcessor(project["word_boundaries"]).parse_srt()
    sources = {source["url"] for source in project.get("sources", [])}
    tokens = [(word, entry["start"]) for entry in entries for word in words(entry["text"])]
    cursor = 0
    resolved = []
    for scene in scenes:
        validate_callouts(scene.get("callouts", []), sources)
        expected = words(scene["narration"])
        window = tokens[cursor:cursor + len(expected)]
        if not expected or [word for word, _ in window] != expected:
            raise ValueError(f"Acoustic narration mismatch in scene {scene['id']}")
        cursor += len(expected)
        scene_end = min(duration, tokens[cursor][1]) if cursor < len(tokens) else duration
        for cue in scene.get("callouts", []):
            anchor = words(cue["phrase"])
            matches = [i for i in range(len(expected)) if expected[i:i + len(anchor)] == anchor]
            if len(matches) != 1:
                raise ValueError(f"Callout phrase must occur once in scene {scene['id']}: {cue['phrase']}")
            start = window[matches[0]][1]
            end = min(scene_end, start + cue["seconds"])
            if end - start < 1 or resolved and start < resolved[-1]["end"]:
                raise ValueError(f"Callout is too short or overlaps in scene {scene['id']}")
            resolved.append({**cue, "scene_id": scene["id"], "start": start, "end": end})
    if cursor != len(tokens):
        raise ValueError("Storyboard does not cover the entire acoustic transcript")
    return resolved


def _ass_time(seconds):
    minutes, rest = divmod(round(seconds * 100), 6000)
    hours, minutes = divmod(minutes, 60)
    whole, fraction = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{whole:02d}.{fraction:02d}"


def ass_document(cues):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Callout,Arial,58,&H00232327,&H00232327,&H00DCEFFC,&H00232327,-1,0,0,0,100,100,0,0,3,17,0,8,84,84,94,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header + "".join(
        f"Dialogue: 0,{_ass_time(cue['start'])},{_ass_time(cue['end'])},Callout,,0,0,0,,"
        f"{{\\fad(140,170)}}{cue['text']}\n"
        for cue in cues
    )
