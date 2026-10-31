"""Single runtime configuration for local video production workers.

Secrets come from environment variables; checked-in JSON files are defaults only.
Existing settings.json files remain compatible during migration.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


DEFAULTS: dict[str, Any] = {
    "settings": {
        "temp_dir": ".temp",
        "parallel_workers": 4,
        "images_per_minute": 20,
        "media_source": "huggingface",
    },
    "article_settings": {"language": "es", "model": "nemotron-3-super:cloud"},
    "serpapi": {"api_key": "", "use_cache": True, "cache_ttl_hours": 24},
    "pexels": {"api_key": ""},
    "huggingface": {"api_key": ""},
    "azure_images": {"endpoint": "", "api_key": "", "model": "MAI-Image-2e"},
    "youtube": {"credentials_file": ".secrets/client_secret.json",
                "token_file": ".secrets/token.json"},
    "tts_edge": {"voice": "es-ES-ElviraNeural", "language": "es"},
    "tts": {"provider": "kokoro"},
    "tts_kokoro": {"voice": "em_alex", "speed": "1.0", "device": "cpu",
                   "python": "output/voice_lab/runtime/Scripts/python.exe",
                   "model_dir": "output/voice_lab/models", "alignment_model": "base"},
    "video_result": {"background_music": ""},
    "llm": {"providers": []},
    "newsapi": {"api_key": ""},
    "currentsapi": {"api_key": ""},
    "upload_type": "youtube",
}


def _merge(destination: dict, overrides: dict) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(destination.get(key), dict):
            _merge(destination[key], value)
        else:
            destination[key] = value


def _getenv(name: str, fallback: Any) -> Any:
    value = os.getenv(name)
    return fallback if value is None else value


def load_runtime_config(config_file: str = "settings.json") -> dict[str, Any]:
    """Resolve legacy JSON, modern defaults and environment overrides.

    A missing *default* settings.json is allowed. A specifically requested
    alternative config file must exist to avoid silently using wrong settings.
    """
    config = copy.deepcopy(DEFAULTS)
    path = Path(config_file)
    if path.is_file():
        with path.open(encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, dict):
            raise ValueError("Configuration root must be a JSON object")
        _merge(config, loaded)
        # Accept the historic pipeline_config.json/settings.example.json layout.
        old_keys = loaded.get("api_keys", {})
        for key, section in (("news_api", "newsapi"), ("pexels_api", "pexels")):
            if old_keys.get(key):
                config[section]["api_key"] = old_keys[key]
        oauth = loaded.get("oauth", {}).get("youtube", {})
        if oauth.get("credentials_file"):
            config["youtube"]["credentials_file"] = oauth["credentials_file"]
    elif path.name != "settings.json":
        raise FileNotFoundError(f"Configuration not found: {config_file}")

    env_fields = {
        ("serpapi", "api_key"): "SERPAPI_API_KEY",
        ("pexels", "api_key"): "PEXELS_API_KEY",
        ("newsapi", "api_key"): "NEWS_API_KEY",
        ("currentsapi", "api_key"): "CURRENTS_API_KEY",
        ("azure_images", "endpoint"): "AZURE_IMAGE_ENDPOINT",
        ("azure_images", "api_key"): "AZURE_IMAGE_API_KEY",
        ("azure_images", "model"): "AZURE_IMAGE_MODEL",
        ("youtube", "credentials_file"): "YOUTUBE_CLIENT_SECRETS_FILE",
        ("youtube", "token_file"): "YOUTUBE_TOKEN_FILE",
        ("article_settings", "language"): "NEWS_LANGUAGE",
        ("article_settings", "model"): "OLLAMA_MODEL",
        ("tts_edge", "voice"): "TTS_VOICE",
        ("tts_edge", "language"): "TTS_LANGUAGE",
        ("tts", "provider"): "TTS_PROVIDER",
        ("tts_kokoro", "voice"): "KOKORO_VOICE",
        ("tts_kokoro", "speed"): "KOKORO_SPEED",
        ("tts_kokoro", "device"): "KOKORO_DEVICE",
        ("tts_kokoro", "python"): "KOKORO_PYTHON",
        ("tts_kokoro", "model_dir"): "KOKORO_MODEL_DIR",
        ("tts_kokoro", "alignment_model"): "KOKORO_ALIGNMENT_MODEL",
        ("settings", "temp_dir"): "VIDEO_TEMP_DIR",
        ("settings", "media_source"): "MEDIA_SOURCE",
        ("video_result", "background_music"): "VIDEO_BACKGROUND_MUSIC",
    }
    for (section, key), var in env_fields.items():
        config[section][key] = _getenv(var, config[section][key])

    config["serpapi"]["use_cache"] = _getenv(
        "SERPAPI_USE_CACHE", str(config["serpapi"]["use_cache"])
    ).lower() in ("1", "yes", "true")
    try:
        config["serpapi"]["cache_ttl_hours"] = int(
            _getenv("SERPAPI_CACHE_TTL_HOURS", config["serpapi"]["cache_ttl_hours"])
        )
    except (ValueError, TypeError) as exc:
        raise ValueError("SERPAPI_CACHE_TTL_HOURS must be an integer") from exc

    # Honor explicitly configured providers; otherwise build a simple failover.
    if not config["llm"].get("providers"):
        providers = []
        if _getenv("OLLAMA_ENABLED", "true").lower() in ("1", "true", "yes"):
            providers.append({
                "type": "ollama",
                "model": _getenv("OLLAMA_MODEL", config["article_settings"]["model"]),
                "endpoint": _getenv("OLLAMA_URL", "http://localhost:11434"),
            })
        if os.getenv("GROQ_API_KEY"):
            providers.append({
                "type": "groq",
                "model": _getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "api_key": os.environ["GROQ_API_KEY"],
            })
        if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
            providers.append({
                "type": "azure",
                "model": _getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini"),
                "endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
                "api_key": os.environ["AZURE_OPENAI_API_KEY"],
            })
        config["llm"]["providers"] = providers

    # Do not mutate the caller's config or write resolved credentials to disk.
    return config
