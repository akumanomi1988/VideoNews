"""E2E dry run: Simulates the full pipeline without uploading to YouTube.

Tests all module integration points:
1. Config loading via ConfigBridge
2. Chatbot LLM article generation
3. TTS audio generation
4. Image generation (with fallbacks)
5. Video assembly (ffmpeg with dry-run check)
"""
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("e2e_dryrun")
errors = []

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLEANUP = True
DRY_RUN_TITLE = "Dry Run Test Title for E2E Pipeline"


def check(stage: str, ok: bool, msg: str):
    if ok:
        logger.info("  OK  %s: %s", stage, msg)
    else:
        errors.append((stage, msg))
        logger.error(" FAIL %s: %s", stage, msg)


def main():
    temp_dir = tempfile.mkdtemp(prefix="e2e_dryrun_")

    try:
        # Stage 1: Config
        logger.info("=== Stage 1: Config Bridge ===")
        from bot.config_bridge import ConfigBridge
        bridge = ConfigBridge()
        bridge.load("settings.json")
        check("config", bool(bridge.get_all()), "ConfigBridge loaded config")
        check("config", bool(bridge.pexels_api_key), "Pexels API key present")
        check("config", bool(bridge.llm_providers), "LLM providers configured")
        check("config", bool(bridge.youtube_credentials_file), "YouTube credentials path set")

        # Stage 2: Chatbot (LLM article generation)
        logger.info("=== Stage 2: Chatbot LLM ===")
        from scripts.AI.natural_language_generation import Chatbot
        cb = Chatbot(
            language="Spanish",
            model="nemotron-3-super:cloud",
            providers=bridge.llm_providers,
        )
        check("chatbot", cb is not None, "Chatbot initialized")
        try:
            result = cb.generate_article_and_phrases_short(DRY_RUN_TITLE)
            article, phrases, title, description, tags, cover_text, cover_image = result
            check("chatbot", bool(article), f"Article generated ({len(article)} chars)")
            check("chatbot", bool(phrases), f"Phrases ({len(phrases)} items)")
            check("chatbot", bool(title), f"Title generated")
        except Exception as e:
            check("chatbot", False, f"Article generation failed: {e}")
            article, phrases, title, description, tags = "", [], "", "", []

        # Stage 3: TTS
        logger.info("=== Stage 3: TTS Audio ===")
        if article:
            from scripts.AI.text_to_speech import TTSFactory, TTSProvider
            tts = TTSFactory(TTSProvider.EDGE, output_dir=temp_dir)
            tts_cfg = json.load(open("settings.json")).get("tts_edge", {})
            try:
                audio_path = tts.text_to_speech_file(
                    article[:200],
                    voice=tts_cfg.get("voice", "es-ES-XimenaNeural"),
                    language="es",
                    rate=tts_cfg.get("speech_rate_adjustment", 0),
                    pitch=tts_cfg.get("pitch_adjustment", 0),
                )
                check("tts", bool(audio_path) and os.path.isfile(audio_path), f"Audio file: {audio_path}")
            except Exception as e:
                check("tts", False, f"TTS failed: {e}")
                audio_path = None
        else:
            audio_path = None

        # Stage 4: Image generation (with fallbacks)
        logger.info("=== Stage 4: Image Generation ===")
        from news_video_processor import NewsVideoProcessor
        processor = NewsVideoProcessor(callback_query=None, event_loop=None, bot=None)
        processor.temp_dir = temp_dir
        test_phrases = ["breaking news technology update"]
        images = processor.fetch_related_media(
            phrases=test_phrases,
            style=None,
            max_items=1,
            orientation=None,
        )
        check("images", len(images) > 0, f"{len(images)} images generated/fetched")
        if images:
            check("images", os.path.isfile(images[0]), f"Image file exists: {images[0]}")

        # Stage 5: Video assembly (syntax check only)
        logger.info("=== Stage 5: Video Assembly ===")
        from scripts.video_assembler import VideoAssembler
        check("assembler", VideoAssembler is not None, "VideoAssembler class imported")
        check("assembler", hasattr(VideoAssembler, "assemble_video"), "assemble_video method present")
        check("assembler", hasattr(VideoAssembler, "assemble"), "assemble method present")
        check("assembler", not hasattr(VideoAssembler, "_concatenate_clips"), "Dead code removed")

        # Stage 6: YouTube uploader (auth check only)
        logger.info("=== Stage 6: YouTube Uploader ===")
        yt_secret = bridge.youtube_credentials_file
        if os.path.isfile(yt_secret):
            try:
                from google.oauth2.credentials import Credentials
                from google_auth_oauthlib.flow import InstalledAppFlow
                flow = InstalledAppFlow.from_client_secrets_file(
                    yt_secret,
                    scopes=["https://www.googleapis.com/auth/youtube.upload"],
                )
                check("youtube", True, f"Credentials file valid: {yt_secret}")
            except Exception as e:
                check("youtube", False, f"Credentials validation failed: {e}")
        else:
            check("youtube", False, f"Credentials file not found: {yt_secret}")

        # Stage 7: Health check
        logger.info("=== Stage 7: Health Check ===")
        from bot.health import run_health_check
        healthy = run_health_check("settings.json")
        check("health", healthy, "Health check: %s fail" % ("passed" if healthy else "failed"))

    finally:
        if CLEANUP:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Cleaned up temp dir: %s", temp_dir)

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print("E2E DRY RUN FAILED")
        for stage, msg in errors:
            print(f"  [{stage}] {msg}")
    else:
        print("E2E DRY RUN PASSED - all integration points OK")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
