"""No-network production prerequisite checks for VideoNews.

Run: python -m scripts.doctor --mode studio|cli --json
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


def audit(mode: str = "studio") -> list[dict]:
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
    ollama = os.getenv("OLLAMA_ENABLED", "false").lower() in ("1", "yes", "true")
    groq = bool(os.getenv("GROQ_API_KEY"))
    azure = bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))
    add("automated_llm", ollama or groq or azure, "optional",
        "Optional automated-provider fallback; ChatGPT-first mode needs no Python LLM key")
    has_mcp = importlib.util.find_spec("mcp") is not None
    add("mcp_sdk", has_mcp, "required" if mode == "studio" else "optional",
        "MCP SDK installed" if has_mcp else "Install requirements-mcp.txt to run the local MCP server")
    add("secure_mcp_tunnel", shutil.which("tunnel-client") is not None, "optional",
        "Install and configure OpenAI tunnel-client to connect ChatGPT to this Windows host")
    add("news_api_credentials", bool(os.getenv("SERPAPI_API_KEY")), "optional",
        "SerpAPI is configured" if os.getenv("SERPAPI_API_KEY") else "Set SERPAPI_API_KEY for live news search")

    media = bool(os.getenv("PEXELS_API_KEY")) or bool(
        os.getenv("AZURE_IMAGE_ENDPOINT") and os.getenv("AZURE_IMAGE_API_KEY")
    )
    add("media_configuration", media, "optional",
        "Configured AI image provider is primary; Pexels requires explicit selection and no placeholder fallback is used")

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

    from scripts.job_registry import review_required
    pending = review_required()
    add("job_reconciliation", not pending, "optional",
        f"{len(pending)} unresolved job(s); run python -m scripts.jobs_cli pending")

    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="VideoNews deployment diagnostics")
    parser.add_argument("--mode", choices=("studio", "cli"), default="studio")
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
