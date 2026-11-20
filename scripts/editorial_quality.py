"""Deterministic diagnostics. Claim support and novelty are editorial judgments."""
from collections import Counter
import re

from scripts.editorial_overlays import words

FORMAT_RANGES = {
    "DAILY_BRIEF": (300, 480),
    "DEEP_DIVE": (360, 600),
    "BREAKING_EXPLAINER": (120, 240),
}

DESK_TOPICS = frozenset({
    "vivienda", "empleo", "impuestos", "ayudas", "consumo", "normativa", "servicios",
})
RUBRIC = ("practical_impact", "novelty", "source_support", "visual_explanation", "timeliness")


def rank_candidates(candidates, published_urls):
    """Rank the editor's evidence-backed assessments, never audience demand."""
    eligible = []
    rejected = []
    for candidate in candidates:
        ratings = candidate["ratings"]
        if (set(ratings) != set(RUBRIC)
                or any(type(v) is not int or not 0 <= v <= 2 for v in ratings.values())):
            raise ValueError("Each editorial criterion must use 0, 1 or 2")
        reason = None
        if candidate["repeats_event"] or set(candidate["source_urls"]) & published_urls:
            reason = "published_overlap"
        elif ratings["source_support"] != 2 or not candidate["source_urls"]:
            reason = "insufficient_corroboration"
        elif not ratings["practical_impact"] or not ratings["novelty"]:
            reason = "no_practical_change"
        elif candidate["topic"] not in DESK_TOPICS and not candidate["exception_reason"].strip():
            reason = "unjustified_exception"
        if reason:
            rejected.append({"title": candidate["title"], "reason": reason})
        else:
            eligible.append(candidate)
    eligible.sort(key=lambda item: (
        item["topic"] in DESK_TOPICS,
        sum(item["ratings"].values()),
        item["ratings"]["practical_impact"],
    ), reverse=True)
    return {"eligible": eligible, "rejected": rejected}


def script_diagnostics(project, duration=None):
    narration = project.get("narration", [])
    script = project.get("script", "")
    sentences = Counter(
        " ".join(tokens)
        for item in re.split(r"[.!?]+", script)
        if len(tokens := words(item)) >= 6
    )
    opening = " ".join(words(script)[:15])
    editorial_format = project.get("editorial_brief", {}).get("editorial_format")
    bounds = FORMAT_RANGES.get(editorial_format)
    return {
        "editorial_format": editorial_format,
        "segment_count": len(narration),
        "word_count": len(words(script)),
        "generic_opening": opening.startswith(("bienvenidos", "en el vídeo de hoy", "hoy vamos a hablar")),
        "repeated_sentences": [s for s, count in sentences.items() if count > 1],
        "measured_duration_seconds": duration,
        "outside_format_guideline": bool(bounds and duration is not None and not bounds[0] <= duration <= bounds[1]),
        "editorial_review_required": [
            "opening_delivers_title_promise", "each_beat_adds_information", "sources_support_each_claim",
        ],
    }
