"""No-network production prerequisite checks for VideoNews.

Run: python -m scripts.doctor --mode cli|telegram --json
Never prints credential values.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def audit(mode: str = "cli") -> list[dict]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    checks = []

    def add(name: str, ok: bool, severity: str, detail: str):
        checks.append({"component": name, "passed": bool(ok), "severity": severity, "detail": detail})

    add("python", sys.version_info[:2] == (3, 11), "required",
        f"Python {sys.version_info.major}.{sys.version_info.minor}; supported: 3.11")
    for tool in ("ffmpeg", "ffprobe"):
        add(tool, shutil.which(tool) is not None, "required", f"{tool} must be in PATH")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
                                      text=True, timeout=5, check=True).stdout
            filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True,
                                     text=True, timeout=5, check=True).stdout
            add("video_codec", "libx264" in encoders, "required", "FFmpeg libx264 encoder")
            add("subtitle_filter", "subtitles" in filters, "required", "FFmpeg libass subtitles filter")
        except (OSError, subprocess.SubprocessError):
            add("video_codec", False, "required", "Could not inspect FFmpeg codecs")
            add("subtitle_filter", False, "required", "Could not inspect FFmpeg filters")

    mode = mode.lower()
    if mode == "telegram":
        raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
        try:
            allowed = [int(value.strip()) for value in raw.split(",") if value.strip()]
        except ValueError:
            allowed = []
        add("telegram_token", bool(os.getenv("TELEGRAM_BOT_TOKEN")), "required", "Bot token configured")
        add("telegram_admins", bool(allowed), "required", "Numeric admin allowlist configured")

    ollama = os.getenv("OLLAMA_ENABLED", "true").lower() in ("1", "yes", "true")
    groq = bool(os.getenv("GROQ_API_KEY"))
    azure = bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))
    add("llm_configuration", ollama or groq or azure, "required",
        "At least one LLM provider configured (reachability not tested)")

    media = bool(os.getenv("PEXELS_API_KEY")) or bool(
        os.getenv("AZURE_IMAGE_ENDPOINT") and os.getenv("AZURE_IMAGE_API_KEY")
    )
    add("media_configuration", media, "optional",
        "Stock or generated images available; otherwise placeholder image fallback")

    tts = os.getenv("TTS_PROVIDER", "edge").lower()
    add("tts_provider", tts in ("edge", "elevenlabs", "bark"), "required",
        f"Voice provider selection: {tts}")
    if tts == "elevenlabs":
        add("elevenlabs", Path(os.getenv("ELEVENLABS_ACCOUNTS_FILE",
             "elevenlabsaccounts.payload.json")).is_file(), "required",
            "Authorized ElevenLabs credentials file present")
    if tts == "bark":
        add("bark_module", importlib.util.find_spec("bark") is not None,
            "required", "Install optional local-ai dependencies")

    if os.getenv("VIDEO_UPLOAD_ENABLED", "false").lower() in ("1", "true", "yes"):
        platform = os.getenv("VIDEO_UPLOAD_PLATFORM", "youtube").lower()
        if platform == "youtube":
            path = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", ".secrets/client_secret.json")
            add("youtube_oauth", Path(path).is_file(), "required", "OAuth client secrets file present")
        elif platform == "tiktok":
            has_token = bool(os.getenv("TIKTOK_ACCESS_TOKEN"))
            token_file = Path(os.getenv("TIKTOK_TOKEN_FILE", ".secrets/tiktok_token.json"))
            add("tiktok_oauth", has_token or token_file.is_file(), "required",
                "Authorized user access token present; creator confirms publication")
        else:
            add("publishing_platform", False, "required", "Use youtube or tiktok")

    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="VideoNews deployment diagnostics")
    parser.add_argument("--mode", choices=("cli", "telegram"), default="cli")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    checks = audit(args.mode)
    if args.json:
        print(json.dumps(checks, indent=2))
    else:
        for check in checks:
            status = "PASS" if check["passed"] else (
                "FAIL" if check["severity"] == "required" else "WARN"
            )
            print(f"[{status:4}] {check['component']:22} {check['detail']}")
    return 1 if any(not item["passed"] and item["severity"] == "required" for item in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
