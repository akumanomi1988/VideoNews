"""
Service layer for handling news-related operations.

This module provides the `NewsService` class, which encapsulates the logic for
fetching news articles from external APIs, managing a cache of these articles,
and providing access to news categories and individual news items.
It uses a news provider (e.g., `NewsAPIProvider`) for external communication.
"""
import time
import logging 
from typing import List, Dict, Any, Optional # For type hinting

from scripts.DataFetcher.news_api_client import NewsAPIProvider # Assuming this path is correct
from scripts.utils.app_logger import trace

# Create a logger instance for this module
logger = logging.getLogger(__name__)

class NewsService:
    """
    A service class for managing news fetching and caching.

    Attributes:
        api_key (Optional[str]): The API key for the news provider.
        default_language (str): Default language for news fetching.
        default_page_size (int): Default number of news items to fetch.
        news_cache (Dict[str, Any]): In-memory cache for news articles.
            Structure: {"timestamp": float, "news": List[Dict[str, Any]], "category": Optional[str]}
        news_provider (NewsAPIProvider): Instance of the news provider client.
        CACHE_TIMEOUT (int): Static variable for cache expiration time in seconds.
    """
    CACHE_TIMEOUT: int = 300  # 5 minutes (300 seconds)

    @trace()
    def __init__(self, api_key: Optional[str], default_language: str = 'en', default_page_size: int = 10):
        """
        Initializes the NewsService.

        Args:
            api_key: The API key for the news provider. Can be None if unavailable,
                     in which case a warning is logged and API calls will fail.
            default_language: Default language for news fetching.
            default_page_size: Default page size for news fetching.
        """
        self.api_key: Optional[str] = api_key
        self.default_language: str = default_language
        self.default_page_size: int = default_page_size
        self.news_cache: Dict[str, Any] = {"timestamp": 0, "news": [], "category": None}
        
        if not self.api_key:
            logger.warning("NewsService initialized without an API key. News fetching will not work.")
        # NewsAPIProvider might raise an error if api_key is None.
        # Depending on NewsAPIProvider's behavior, this might need a try-except or conditional instantiation.
        # For now, assume NewsAPIProvider can handle api_key=None or it's checked before use.
        self.news_provider: NewsAPIProvider = NewsAPIProvider(api_key=self.api_key) 
        logger.debug(f"NewsService initialized with language '{default_language}' and page size {default_page_size}.")

    @trace()
    def is_cache_expired(self) -> bool:
        """Checks if the news cache has expired based on `CACHE_TIMEOUT`."""
        expired: bool = time.time() - self.news_cache["timestamp"] > self.CACHE_TIMEOUT
        if expired:
            logger.debug("News cache is expired.")
        else:
            logger.debug("News cache is still valid.")
        return expired

    @trace()
    def get_news_categories(self) -> List[str]:
        """
        Returns a predefined list of available news categories.
        
        Returns:
            A list of strings, where each string is a news category.
        """
        logger.debug("Retrieving news categories.")
        return ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']

    @trace()
    def fetch_news(self, category: str, language: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetches news for a given category.
        Uses cached news if available and not expired, otherwise fetches fresh news.
        Args:
            category: The category of news to fetch.
            language: The language for the news. If None, uses the service's default language.
            limit: The number of news items to fetch. If None, uses the service's default page size.
        
        Returns:
            A list of dictionaries, where each dictionary represents a news item.
            Returns an empty list if fetching fails or no API key is available.
        """
        current_language: str = language if language else self.default_language
        current_limit: int = limit if limit else self.default_page_size
        cache_category: Optional[str] = self.news_cache.get("category")

        # Determine if cache needs refresh
        refresh_needed = (
            not self.news_cache["news"] or 
            self.is_cache_expired() or 
            cache_category != category
        )

        if refresh_needed:
            logger.info(f"Cache miss or expired for category '{category}'. Fetching fresh news. "
                        f"Previous cache category was '{cache_category}'.")
            if not self.api_key:
                logger.error("Cannot fetch news: API key is not set.")
                return []
            
            try:
                logger.debug(f"Fetching news from provider: category='{category}', lang='{current_language}', limit={current_limit}")
                latest_news_data: List[Dict[str, Any]] = self.news_provider.get_latest_news(
                    language=current_language,
                    limit=current_limit,
                    category=category
                )
                self.news_cache["news"] = latest_news_data
                self.news_cache["timestamp"] = time.time()
                self.news_cache["category"] = category 
                logger.info(f"News cache updated for category: {category} with {len(latest_news_data)} items.")
            except Exception as e:
                logger.error(f"Error fetching news from provider for category '{category}': {e}", exc_info=True)
                # Return old cache if it matches the requested category, otherwise empty list
                if self.news_cache.get("category") == category:
                    return self.news_cache.get("news", [])
                return []
        else:
            logger.info(f"Using cached news for category: {category}.")
        
        return self.news_cache.get("news", [])

    @trace()
    def get_cached_news(self) -> List[Dict[str, Any]]:
        """
        Returns the currently cached list of news items.
        
        Returns:
            A list of dictionaries, where each dictionary is a news item.
            Returns an empty list if the cache is empty.
        """
        logger.debug("Accessing get_cached_news.")
        return self.news_cache.get("news", [])

    @trace()
    def get_cached_news_item(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific news item from the cache by its index.

        Args:
            index: The index of the news item to retrieve from the cached list.
        
        Returns:
            A dictionary representing the news item if found at the given index, 
            otherwise None.
        """
        cached_news: List[Dict[str, Any]] = self.get_cached_news()
        if 0 <= index < len(cached_news):
            logger.debug(f"Retrieved cached news item at index {index}.")
            return cached_news[index]
        logger.warning(f"Failed to retrieve cached news item: index {index} out of range (0-{len(cached_news)-1}).")
        return None

if __name__ == '__main__':
    # Basic logging configuration for standalone execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Example Usage (requires a valid API key to be set as an environment variable or passed)
    # Make sure to have a .env file with NEWS_API_KEY or pass it directly for testing
    import os
    from dotenv import load_dotenv
    load_dotenv() # Load .env file for NEWS_API_KEY

    demo_api_key = os.getenv("NEWS_API_KEY")
    if not demo_api_key:
        logger.error("Please set the NEWS_API_KEY environment variable for demo.")
    else:
        news_service = NewsService(api_key=demo_api_key, default_language='en', default_page_size=5)
        
        logger.info(f"Available categories: {news_service.get_news_categories()}")
        
        logger.info("\nFetching 'technology' news...")
        tech_news = news_service.fetch_news(category='technology')
        for i, item in enumerate(tech_news):
            logger.info(f"{i+1}. {item.get('title', 'No Title')}")

        logger.info("\nFetching 'technology' news again (should use cache)...")
        tech_news_cached = news_service.fetch_news(category='technology')
        # assert tech_news == tech_news_cached 

        logger.info("\nFetching 'sports' news...")
        sports_news = news_service.fetch_news(category='sports')
        for i, item in enumerate(sports_news):
            logger.info(f"{i+1}. {item.get('title', 'No Title')}")

        logger.info("\nGetting specific cached news item (index 0 from sports):")
        item_0 = news_service.get_cached_news_item(0)
        if item_0:
            logger.info(f"Cached item [0]: {item_0.get('title')}")
        else:
            logger.warning("Item not found or cache empty for index 0.")
