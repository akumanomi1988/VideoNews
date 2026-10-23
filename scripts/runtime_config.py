"""Load the legacy-compatible runtime config without committing credentials.

The bundled example contains no secrets. Environment overrides are applied only
in memory and never serialized to disk.
"""

import json
import os
from pathlib import Path
from typing import Any


EXAMPLE = Path(__file__).resolve().parent.parent / "settings.runtime.example.json"


def load_runtime_config(path: str = "settings.json") -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        source = EXAMPLE
    with source.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError("Runtime settings must be a JSON object")

    overrides = (
        ("SERPAPI_API_KEY", "serpapi", "api_key"),
        ("PEXELS_API_KEY", "pexels", "api_key"),
        ("NEWS_API_KEY", "newsapi", "api_key"),
        ("AZURE_IMAGE_ENDPOINT", "azure_images", "endpoint"),
        ("AZURE_IMAGE_API_KEY", "azure_images", "api_key"),
        ("AZURE_IMAGE_MODEL", "azure_images", "model"),
        ("YOUTUBE_CREDENTIALS_FILE", "youtube", "credentials_file"),
        ("ARTICLE_LANGUAGE", "article_settings", "language"),
        ("ARTICLE_MODEL", "article_settings", "model"),
        ("TTS_VOICE", "tts_edge", "voice"),
        ("TTS_LANGUAGE", "tts_edge", "language"),
    )
    for env, section, name in overrides:
        value = os.getenv(env)
        if value:
            config.setdefault(section, {})[name] = value

    # Opt-in YouTube publishing. Local rendering is the safe default.
    enabled = os.getenv("YOUTUBE_UPLOAD_ENABLED", "").lower() in ("1", "true", "yes")
    config.setdefault("youtube", {})["enabled"] = enabled
    config["upload_type"] = "youtube" if enabled else "local"
    config.setdefault("settings", {}).setdefault("temp_dir", ".videonews-tmp")
    config["settings"].setdefault("output_dir", "output")
    config.setdefault("article_settings", {}).setdefault("language", "es")
    config["article_settings"].setdefault("model", "nemotron-3-super:cloud")
    return config
