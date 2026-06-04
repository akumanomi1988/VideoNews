import os
import logging # Added for logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a logger instance for this module
logger = logging.getLogger(__name__)

def get_telegram_token() -> str | None:
    """Retrieves the Telegram bot token from environment variables."""
    return os.getenv("TELEGRAM_BOT_TOKEN")

def get_news_api_key() -> str | None:
    """Retrieves the News API key from environment variables."""
    return os.getenv("NEWS_API_KEY")

def get_news_api_country() -> str:
    """Retrieves the News API country from environment variables, defaulting to 'us'."""
    return os.getenv("NEWS_API_COUNTRY", "us")

def get_news_api_page_size() -> int:
    """Retrieves the News API page size from environment variables, defaulting to 10."""
    val = os.getenv("NEWS_API_PAGE_SIZE", "10")
    try:
        return int(val)
    except (ValueError, TypeError):
        logger.warning("Invalid NEWS_API_PAGE_SIZE: '%s', using default 10", val)
        return 10

def get_tts_language() -> str:
    """Retrieves the TTS language from environment variables, defaulting to 'en-US'."""
    return os.getenv("TTS_LANGUAGE", "en-US")

# For compatibility with the old structure, we can still provide a settings object
# although the primary way to access settings should be through the get_ functions.
class Settings:
    """
    A compatibility class that provides access to configuration settings via properties.
    This is intended for use by older parts of the system that expect a settings object.
    The primary way to access settings should be through the `get_*` functions.
    """
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str | None:
        """Retrieves the Telegram bot token via `get_telegram_token()`."""
        return get_telegram_token()

    @property
    def NEWS_API_KEY(self) -> str | None:
        """Retrieves the News API key via `get_news_api_key()`."""
        return get_news_api_key()

    @property
    def NEWS_API_COUNTRY(self) -> str:
        """Retrieves the News API country via `get_news_api_country()`."""
        return get_news_api_country()

    @property
    def NEWS_API_PAGE_SIZE(self) -> int:
        """Retrieves the News API page size via `get_news_api_page_size()`."""
        return get_news_api_page_size()

    @property
    def TTS_LANGUAGE(self) -> str:
        """Retrieves the TTS language via `get_tts_language()`."""
        return get_tts_language()

settings: Settings = Settings()

if __name__ == '__main__':
    # Example usage:
    # Basic logging configuration for standalone execution (if any other module doesn't set it up)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logger.info(f"Telegram Bot Token: {'***' if get_telegram_token() else 'NOT SET'}")
    logger.info(f"News API Key: {'***' if get_news_api_key() else 'NOT SET'}")
    logger.info(f"News API Country: {get_news_api_country()}")
    logger.info(f"News API Page Size: {get_news_api_page_size()}")
    logger.info(f"TTS Language: {get_tts_language()}")

    # Example usage with the settings object
    logger.info(f"Telegram Bot Token from settings object: {'***' if settings.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
