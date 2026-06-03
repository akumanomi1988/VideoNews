"""Verification script for Iteration 1: validate config bridge across all modules."""
import json
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("check_config")

errors = []
warnings = []


def check(module: str, condition: bool, msg: str):
    if condition:
        logger.info("  OK  %s: %s", module, msg)
    else:
        errors.append((module, msg))
        logger.error(" FAIL %s: %s", module, msg)


def warn(module: str, msg: str):
    warnings.append((module, msg))
    logger.warning(" WARN %s: %s", module, msg)


# --- 1. Load ConfigBridge ---
sys.path.insert(0, os.path.dirname(__file__))
try:
    from bot.config_bridge import ConfigBridge, normalize_config, load_json
    logger.info("ConfigBridge imported OK")
except ImportError as e:
    logger.error("FAIL: ConfigBridge import failed: %s", e)
    sys.exit(1)

bridge = ConfigBridge()

# --- 2. Load from settings.json ---
if not os.path.isfile("settings.json"):
    warn("settings.json", "File not found, using pipeline_config.json")
else:
    raw = load_json("settings.json")
    check("settings.json", raw is not None, "File is valid JSON")
    if raw:
        normalized = normalize_config(raw)

        # Verify all critical keys exist
        required_keys = [
            "temp_dir", "media_source", "pexels_api_key", "flux_api_key",
            "newsapi_api_key", "llm_providers", "tts_voice", "tts_language",
            "youtube_credentials_file", "background_music",
        ]
        for key in required_keys:
            check("config_bridge", key in normalized, f"Key '{key}' exists in normalized config")

        # Check empty keys
        for key in ["pexels_api_key", "flux_api_key", "newsapi_api_key"]:
            if key in normalized and not normalized[key]:
                warn("settings.json", f"Key '{key}' is empty - feature will fail")

# --- 3. Verify VideoService can read config via bridge ---
try:
    from bot.services.video_service import VideoService
    vs = VideoService()
    check("VideoService", vs is not None, "VideoService instantiated OK")
except Exception as e:
    check("VideoService", False, f"Instantiation failed: {e}")

# --- 4. Verify NewsVideoProcessor config loading ---
try:
    from news_video_processor import NewsVideoProcessor, CONFIG_SETTINGS
    processor = NewsVideoProcessor(callback_query=None, event_loop=None, bot=None)
    config = processor.config
    check(
        "NewsVideoProcessor",
        CONFIG_SETTINGS in config and "temp_dir" in config.get(CONFIG_SETTINGS, {}),
        "config loaded and CONFIG_SETTINGS present",
    )
except Exception as e:
    check("NewsVideoProcessor", False, f"Config load failed: {e}")

# --- 5. Verify viral agent config bridge ---
try:
    vc = bridge.as_viral_agent_config()
    check("viral_agent", "newsapi_key" in vc, "ConfigBridge provides newsapi_key")
    check("viral_agent", isinstance(vc.get("keywords", {}), dict), "ConfigBridge provides keywords dict")
except Exception as e:
    check("viral_agent", False, f"Config bridge failed: {e}")

# --- 6. Verify PipelineContainer config normalization ---
try:
    from scripts.utils.container import PipelineContainer
    pc = PipelineContainer({})
    check("PipelineContainer", pc.config is not None, "PipelineContainer initialized with empty config")
except Exception as e:
    check("PipelineContainer", False, f"Init failed: {e}")

# --- 7. Summary ---
print("\n" + "=" * 60)
if errors:
    print(f"{' FAILED ':=^60}")
    for module, msg in errors:
        print(f"  [{module}] {msg}")
else:
    print(f"{' ALL CHECKS PASSED ':=^60}")

if warnings:
    print(f"\n{' WARNINGS ':-^60}")
    for module, msg in warnings:
        print(f"  [{module}] {msg}")

sys.exit(1 if errors else 0)
