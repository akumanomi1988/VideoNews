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


# Measured on Kokoro em_alex at speed 1.0: 631 Spanish words -> 233 s.
SPANISH_WORDS_PER_SECOND = 2.7
GREETING_OPENINGS = ("bienvenidos", "bienvenidas", "hola", "en el vídeo de hoy", "hoy vamos a hablar")
CTA_WORDS = frozenset({"suscríbete", "suscribete", "campana", "like"})


def format_range(editorial_format):
    return FORMAT_RANGES.get(editorial_format)


def estimated_duration_seconds(script):
    return round(len(words(script)) / SPANISH_WORDS_PER_SECOND, 1)


def script_diagnostics(project, duration=None):
    narration = project.get("narration", [])
    script = project.get("script", "")
    sentences = Counter(
        " ".join(parts)
        for item in re.split(r"[.!?]+", script)
        if len(parts := words(item)) >= 6
    )
    tokens = words(script)
    opening = " ".join(tokens[:15])
    brief = project.get("editorial_brief", {})
    editorial_format = brief.get("editorial_format")
    bounds = format_range(editorial_format)
    estimate = estimated_duration_seconds(script)
    measured_or_estimated = duration if duration is not None else estimate
    if bounds:
        # Editorial formats open on a sourced fact; the welcome and early CTA
        # belong to the classic single-story template only.
        generic_opening = opening.startswith(GREETING_OPENINGS)
    else:
        generic_opening = opening.startswith("en el vídeo de hoy")
    first_quarter = set(tokens[:max(1, len(tokens) // 4)])
    target = brief.get("target_duration_seconds")
    tolerance = None
    if isinstance(target, int):
        tolerance = max(brief.get("duration_tolerance_seconds", 0), round(target * 0.10))
    return {
        "editorial_format": editorial_format,
        "segment_count": len(narration),
        "word_count": len(tokens),
        "estimated_duration_seconds": estimate,
        "generic_opening": generic_opening,
        "early_cta_in_editorial_format": bool(bounds and first_quarter & CTA_WORDS),
        "repeated_sentences": [s for s, count in sentences.items() if count > 1],
        "measured_duration_seconds": duration,
        "outside_format_guideline": bool(bounds and not bounds[0] <= measured_or_estimated <= bounds[1]),
        "outside_target_duration": bool(tolerance is not None
                                        and abs(measured_or_estimated - target) > tolerance),
        "editorial_review_required": [
            "opening_delivers_title_promise", "each_beat_adds_information", "sources_support_each_claim",
        ],
    }
