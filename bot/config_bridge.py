import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("Cannot load config '%s': %s", path, e)
        return None


def normalize_config(
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}

    settings = raw.get("settings", {})

    cfg["temp_dir"] = raw.get("temp_dir") or settings.get("temp_dir", ".temp")
    cfg["media_source"] = settings.get("media_source", "huggingface")
    cfg["parallel_workers"] = settings.get("parallel_workers", 6)
    cfg["images_per_minute"] = settings.get("images_per_minute", 20)
    cfg["media_source"] = settings.get("media_source", "huggingface")

    pexels = raw.get("pexels", {})
    cfg["pexels_api_key"] = pexels.get("api_key", "")

    huggingface = raw.get("huggingface", {})
    cfg["flux_api_key"] = huggingface.get("api_key", "")

    newsapi = raw.get("newsapi", {})
    cfg["newsapi_api_key"] = newsapi.get("api_key", "")
    cfg["newsapi_country"] = newsapi.get("country", "us")
    cfg["newsapi_category"] = newsapi.get("category", "general")
    cfg["newsapi_page_size"] = newsapi.get("page_size", 5)

    currentsapi = raw.get("currentsapi", {})
    cfg["currentsapi_api_key"] = currentsapi.get("api_key", "")

    article_settings = raw.get("article_settings", {})
    cfg["article_language"] = article_settings.get("language", "Spanish")
    cfg["article_model"] = article_settings.get("model", "nemotron-3-super:cloud")

    llm = raw.get("llm", {})
    cfg["llm_providers"] = llm.get("providers", [])

    tts_edge = raw.get("tts_edge", {})
    cfg["tts_voice"] = tts_edge.get("voice", "es-ES-XimenaNeural")
    cfg["tts_language"] = tts_edge.get("language", "es")
    cfg["tts_speech_rate"] = tts_edge.get("speech_rate_adjustment", 0)
    cfg["tts_pitch"] = tts_edge.get("pitch_adjustment", 0)

    elevenlabs = raw.get("elevenlabs", {})
    cfg["elevenlabs_credentials_path"] = elevenlabs.get(
        "credentials_path", "elevenlabsaccounts.payload.json"
    )
    cfg["elevenlabs_quota_min"] = elevenlabs.get("quota_min", 1000)

    azure_images = raw.get("azure_images", {})
    cfg["azure_image_endpoint"] = azure_images.get("endpoint", "")
    cfg["azure_image_api_key"] = azure_images.get("api_key", "")
    cfg["azure_image_model"] = azure_images.get(
        "model", "MAI-Image-2e"
    )

    youtube = raw.get("youtube", {})
    cfg["youtube_credentials_file"] = youtube.get(
        "credentials_file", "secrets/client_secret.json"
    )

    tiktok = raw.get("tiktok", {})
    cfg["tiktok_app_id"] = tiktok.get("app_id", "")
    cfg["tiktok_client_secret"] = tiktok.get("client_secret", "")
    cfg["tiktok_client_id"] = tiktok.get("client_id", "")

    video_result = raw.get("video_result", {})
    cfg["background_music"] = video_result.get("background_music", "")
    cfg["aspect_ratio"] = video_result.get("aspect_ratio", "9:16")

    telegram = raw.get("telegram", {})
    cfg["telegram_bot_token"] = telegram.get("bot_token", "")

    meta = raw.get("meta", {})
    cfg["facebook_page_id"] = meta.get("facebook_page_id", "")
    cfg["facebook_token"] = meta.get("facebook_token", "")
    cfg["instagram_token"] = meta.get("instagram_token", "")

    cfg["rss_feeds"] = raw.get("rss_feeds", [])
    cfg["virality_threshold"] = raw.get("virality_threshold", 0.5)
    cfg["time_window_days"] = raw.get("time_window_days", 2)
    cfg["keywords"] = raw.get("keywords", {})

    for k, v in raw.items():
        if k not in cfg:
            cfg[k] = v

    return cfg


class ConfigBridge:
    _instance: Optional["ConfigBridge"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> "ConfigBridge":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(
        self,
        settings_path: str = "settings.json",
        pipeline_config_path: str = "pipeline_config.json",
    ) -> None:
        settings_raw = load_json(settings_path) or {}
        pipeline_raw = load_json(pipeline_config_path) or {}

        if settings_raw:
            self._config = normalize_config(settings_raw)
            logger.info(
                "Config loaded from %s (settings.json format)", settings_path
            )
        elif pipeline_raw:
            self._config = normalize_config(pipeline_raw)
            logger.info(
                "Config loaded from %s (pipeline_config.json format, limited keys)",
                pipeline_config_path,
            )
        else:
            logger.warning(
                "No config file found at %s or %s. Using defaults.",
                settings_path,
                pipeline_config_path,
            )
            self._config = normalize_config({})

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._config)

    def as_viral_agent_config(self) -> Dict[str, Any]:
        return {
            "newsapi_key": self.get("newsapi_api_key", ""),
            "currentsapi_key": self.get("currentsapi_api_key", ""),
            "rss_feeds": self.get("rss_feeds", []),
            "virality_threshold": self.get("virality_threshold", 0.5),
            "time_window_days": self.get("time_window_days", 2),
            "keywords": self.get("keywords", {}),
        }

    @property
    def temp_dir(self) -> str:
        return self.get("temp_dir", ".temp")

    @property
    def pexels_api_key(self) -> str:
        return self.get("pexels_api_key", "")

    @property
    def flux_api_key(self) -> str:
        return self.get("flux_api_key", "")

    @property
    def llm_providers(self) -> List[Dict[str, Any]]:
        return self.get("llm_providers", [])

    @property
    def tts_voice(self) -> str:
        return self.get("tts_voice", "es-ES-XimenaNeural")

    @property
    def tts_language(self) -> str:
        return self.get("tts_language", "es")

    @property
    def youtube_credentials_file(self) -> str:
        return self.get("youtube_credentials_file", "secrets/client_secret.json")

    @property
    def background_music(self) -> str:
        return self.get("background_music", "")

    @property
    def telegram_bot_token(self) -> str:
        return self.get("telegram_bot_token", "")
