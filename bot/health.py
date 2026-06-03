"""Startup health check for the VideoNews bot. Verifies all external services."""
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("health")

checks: Dict[str, Dict[str, Any]] = {}


def _check(name: str, ok: bool, detail: str = ""):
    checks[name] = {"ok": ok, "detail": detail}
    level = logger.info if ok else logger.warning
    level("  %s %s: %s", "OK" if ok else "FAIL", name, detail)


def run_health_check(settings_path: str = "settings.json") -> bool:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    _check("Python version", sys.version_info >= (3, 11), sys.version)

    # 1. Config files
    _check("settings.json", os.path.isfile(settings_path), settings_path)
    _check(
        "pipeline_config.json",
        os.path.isfile("pipeline_config.json"),
        "pipeline_config.json",
    )

    # 2. Telegram token
    try:
        from bot.config import get_telegram_token

        token = get_telegram_token()
        _check("TELEGRAM_BOT_TOKEN", bool(token), "present" if token else "missing")
    except Exception as e:
        _check("TELEGRAM_BOT_TOKEN", False, str(e))

    # 3. News API
    try:
        from bot.config import get_news_api_key

        news_key = get_news_api_key()
        _check("NEWS_API_KEY", bool(news_key), "present" if news_key else "missing")
    except Exception as e:
        _check("NEWS_API_KEY", False, str(e))

    # 4. ImageMagick
    magick = os.environ.get("IMAGEMAGICK_BINARY", "")
    magick_home = os.environ.get("MAGICK_HOME", "")
    if magick_home and not magick:
        magick = os.path.join(magick_home, "magick.exe") if os.name == "nt" else os.path.join(magick_home, "magick")
    _check(
        "ImageMagick binary",
        os.path.isfile(magick) if magick else os.path.isfile("C:\\Program Files\\ImageMagick-7.1.2-Q16-HDRI\\magick.exe" if os.name == "nt" else "/usr/bin/convert"),
        magick or "default paths used",
    )

    # 5. FFmpeg
    try:
        import subprocess

        r = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        ver = r.stdout.splitlines()[0] if r.stdout else "unknown"
        _check("ffmpeg", r.returncode == 0, ver)
    except Exception as e:
        _check("ffmpeg", False, str(e))

    # 6. Temporary directory
    from bot.config_bridge import ConfigBridge

    bridge = ConfigBridge()
    bridge.load(settings_path)
    temp_dir = bridge.temp_dir
    try:
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        _check("temp_dir", True, temp_dir)
    except Exception as e:
        _check("temp_dir", False, str(e))

    # 7. YouTube credentials
    yt_cred = bridge.youtube_credentials_file
    _check("YouTube credentials", os.path.isfile(yt_cred) if yt_cred else False, yt_cred or "not configured")

    # 8. LLM providers
    providers = bridge.llm_providers
    if providers:
        for p in providers:
            ptype = p.get("type", "unknown")
            pmodel = p.get("model", "")
            _check(f"LLM provider: {ptype}", bool(pmodel), pmodel)
    else:
        _check("LLM providers", False, "no providers configured")

    # 9. Pexels API
    pexels_key = bridge.pexels_api_key
    _check("Pexels API key", bool(pexels_key), "present" if pexels_key else "missing")

    # 10. HuggingFace API
    hf_key = bridge.get("flux_api_key", "")
    _check("HuggingFace API key", bool(hf_key), "present" if hf_key else "missing")

    # 11. Groq API (if configured)
    for p in providers:
        if p.get("type") == "groq":
            _check("Groq API key", bool(p.get("api_key")), "present" if p.get("api_key") else "missing")

    # Summary
    ok_count = sum(1 for c in checks.values() if c["ok"])
    fail_count = sum(1 for c in checks.values() if not c["ok"])
    print(f"\n{'='*60}")
    print(f"Health check: {ok_count} passed, {fail_count} failed")
    return fail_count == 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    success = run_health_check()
    sys.exit(0 if success else 1)
