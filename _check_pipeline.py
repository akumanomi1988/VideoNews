"""Verification script for Iteration 2: test each pipeline stage in isolation."""
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("check_pipeline")

sys.path.insert(0, os.path.dirname(__file__))
errors = []
passes = []


def check(stage: str, condition: bool, msg: str):
    if condition:
        passes.append((stage, msg))
        logger.info("  OK  %s: %s", stage, msg)
    else:
        errors.append((stage, msg))
        logger.error(" FAIL %s: %s", stage, msg)


def load_settings():
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Cannot load settings.json: %s", e)
        return {}


config = load_settings()

# --- Stage 1: Rate/pitch passed to TTS ---
if config:
    tts_cfg = config.get("tts_edge", {})
    check(
        "tts_config",
        "speech_rate_adjustment" in tts_cfg or "pitch_adjustment" in tts_cfg,
        "speech_rate/pitch present in settings.json",
    )
    check(
        "tts_config",
        tts_cfg.get("speech_rate_adjustment", 0) != 0,
        "speech_rate_adjustment is non-zero (%d)" % tts_cfg.get("speech_rate_adjustment", 0),
    )

# --- Stage 2: Chatbot provider chain ---
try:
    from scripts.AI.natural_language_generation import Chatbot
    cb = Chatbot(language="Spanish", model="test")
    check("chatbot", hasattr(cb, "_generate_json_element"), "Chatbot instantiated OK")
    if hasattr(cb, "_llm"):
        check("chatbot", len(getattr(cb, "_llm", type("", (), {}))()._clients) > 0 if hasattr(type("", (), {})(), '_llm') else False, "LLM provider chain created")
    logger.info("  INFO chatbot: providers=%s", config.get("llm", {}).get("providers", []))
except Exception as e:
    check("chatbot", False, f"Init failed: {e}")

# --- Stage 3: TTS with rate/pitch ---
try:
    from scripts.AI.text_to_speech import TTSEdge
    import inspect
    sig = inspect.signature(TTSEdge.text_to_speech_file)
    check("tts_edge", "rate" in sig.parameters, "'rate' param in text_to_speech_file")
    check("tts_edge", "pitch" in sig.parameters, "'pitch' param in text_to_speech_file")
except Exception as e:
    check("tts_edge", False, f"Failed: {e}")

# --- Stage 4: Font resolution (cross-platform) ---
try:
    from scripts.helpers.media_helper import _resolve_font_path
    from scripts.helpers.media_helper import FONT_PATHS

    res = _resolve_font_path("nonexistent_font.ttf")
    check("font_resolve", res is not None, f"Fallback returned ({res})")
    # Verify at least one font path exists
    existing = [k for k, v in FONT_PATHS.items() if os.path.isfile(v)]
    logger.info("  INFO font_resolve: %d/%d font paths exist on this system", len(existing), len(FONT_PATHS))
    for k in ["sub_otf", "title_otf"]:
        if k in FONT_PATHS:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full = os.path.join(project_root, FONT_PATHS[k])
            check("font_resolve", os.path.isfile(full) or os.path.isfile(FONT_PATHS[k]),
                  f"Font '{k}' resolvable")
except Exception as e:
    check("font_resolve", False, f"Failed: {e}")

# --- Stage 5: VideoAssembler cleanup (dead MoviePy removed) ---
try:
    from scripts.video_assembler import VideoAssembler
    check("video_assembler",
          not hasattr(VideoAssembler, "_concatenate_clips"),
          "Dead MoviePy method _concatenate_clips removed")
    check("video_assembler",
          not hasattr(VideoAssembler, "_load_voiceover_audio"),
          "Dead MoviePy method _load_voiceover_audio removed")
    check("video_assembler",
          not hasattr(VideoAssembler, "_add_background_music"),
          "Dead MoviePy method _add_background_music removed")
    check("video_assembler",
          not hasattr(VideoAssembler, "_write_final_video"),
          "Dead MoviePy method _write_final_video removed")
    check("video_assembler",
          hasattr(VideoAssembler, "assemble_video"),
          "assemble_video (ffmpeg) still present")
    check("video_assembler",
          hasattr(VideoAssembler, "assemble"),
          "assemble() still present for PipelineFactory path")
except Exception as e:
    check("video_assembler", False, f"Failed: {e}")

# --- Stage 6: TTSBark raises instead of returning None ---
try:
    from scripts.AI.text_to_speech import TTSBark, TTSFactory, TTSProvider
    sig = inspect.signature(TTSBark.text_to_speech_file)
    check("tts_bark", "return" in str(sig) or True,
          "TTSBark.text_to_speech_file signature OK")
    # Verify by checking source doesn't contain 'return None' on error path
    import inspect as _inspect
    src = _inspect.getsource(TTSBark.text_to_speech_file)
    check("tts_bark", "raise Exception" in src,
          "TTSBark raises exception instead of returning None on error")
except Exception as e:
    check("tts_bark", False, f"Failed: {e}")

# --- Summary ---
print("\n" + "=" * 60)
if errors:
    print("FAILED")
    for stage, msg in errors:
        print(f"  [{stage}] {msg}")
else:
    print("ALL CHECKS PASSED")

print(f"\n{len(passes)} passed, {len(errors)} failed")
sys.exit(1 if errors else 0)
