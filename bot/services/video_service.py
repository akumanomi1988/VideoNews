"""
Service layer for video processing operations.

This module provides the `VideoService` class, which encapsulates the logic for
processing news items into different video formats (short and long) and for
handling the processing of viral news items. It utilizes `NewsVideoProcessor`
for individual video creation and `NewsProcessor` for fetching viral news.
"""
import json 
import logging 
from typing import Dict, Any, Optional, Callable, Awaitable # For type hinting

from telegram import CallbackQuery # For type hinting callback_query

from news_video_processor import NewsVideoProcessor 
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news

# Create a logger instance for this module
logger = logging.getLogger(__name__)

class VideoService:
    """
    A service class for processing news into videos and handling viral news processing.
    It acts as a wrapper around `NewsVideoProcessor` for individual video tasks
    and `NewsProcessor` for the viral news pipeline.
    """

    def __init__(self) -> None:
        """
        Initializes the VideoService.
        Currently, no specific state is stored in the instance itself, as processors
        are instantiated on-demand per method call.
        """
        logger.debug("VideoService initialized.")

    def process_short_news(self, 
                           news_item_title: str, 
                           news_item_description: str, 
                           callback_query: Optional[CallbackQuery] = None
                          ) -> Dict[str, Any]:
        """
        Processes a news item into a short video format.
        Args:
            news_item_title: The title of the news item.
            news_item_description: The description of the news item.
            callback_query: Optional Telegram CallbackQuery object, which might be
                            used by `NewsVideoProcessor` for progress updates.
        Returns:
            A dictionary containing the response from the video processor,
            typically including video ID and snippet information.
        Raises:
            Exception: Re-raises exceptions from `NewsVideoProcessor`.
        """
        logger.info(f"Processing short news - Title: {news_item_title}")
        try:
            processor = NewsVideoProcessor(callback_query=callback_query)
            news_data: Dict[str, str] = {"title": news_item_title, "description": news_item_description}
            response_data: Dict[str, Any] = processor.process_latest_news_in_short_format(news_data)
            logger.debug(f"Short news processing successful for title: {news_item_title}")
            return response_data
        except Exception as e:
            logger.error(f"Error during process_short_news for title '{news_item_title}': {e}", exc_info=True)
            raise 

    def process_long_news(self, 
                          news_item_title: str, 
                          news_item_description: str, 
                          callback_query: Optional[CallbackQuery] = None
                         ) -> Dict[str, Any]:
        """
        Processes a news item into a long video format.
        Args:
            news_item_title: The title of the news item.
            news_item_description: The description of the news item.
            callback_query: Optional Telegram CallbackQuery object.
        Returns:
            A dictionary containing the response from the video processor.
        Raises:
            Exception: Re-raises exceptions from `NewsVideoProcessor`.
        """
        logger.info(f"Processing long news - Title: {news_item_title}")
        try:
            processor = NewsVideoProcessor(callback_query=callback_query)
            news_data: Dict[str, str] = {"title": news_item_title, "description": news_item_description}
            response_data: Dict[str, Any] = processor.process_latest_news_in_long_format(news_data)
            logger.debug(f"Long news processing successful for title: {news_item_title}")
            return response_data
        except Exception as e:
            logger.error(f"Error during process_long_news for title '{news_item_title}': {e}", exc_info=True)
            raise 

    async def process_viral_news(self, 
                                 num_to_process: Optional[int] = None, 
                                 message_callback: Optional[Callable[[str], Awaitable[None]]] = None, 
                                 config_file_path: str = 'config.json'
                                ) -> None:
        """
        Processes viral news items fetched by `NewsProcessor`.

        This method iteratively fetches viral news and processes them into short videos.
        It uses a `message_callback` to send progress and status updates.

        Args:
            num_to_process: The number of viral news items to process. 
                            If None, attempts to process all available items from the feed.
            message_callback: An async function that takes a string message and sends it
                              (e.g., to a Telegram chat).
            config_file_path: Path to the JSON configuration file required by `NewsProcessor`.
        """
        logger.info(f"Starting process_viral_news. Number to process: {num_to_process if num_to_process else 'all'}")

        async def send_msg(text: str, level: int = logging.INFO) -> None:
            """Helper to send message via callback and log it."""
            if message_callback:
                await message_callback(text)
            logger.log(level, f"ViralNewsProcessing: {text}")


        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config: Dict[str, Any] = json.load(f)
            logger.debug(f"Successfully loaded configuration from {config_file_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file '{config_file_path}' not found for viral news processing.", exc_info=True)
            await send_msg(f"Error: Configuration file '{config_file_path}' not found. Cannot process viral news. ❌", logging.ERROR)
            return
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from '{config_file_path}'.", exc_info=True)
            await send_msg(f"Error: Could not decode JSON from '{config_file_path}'. Cannot process viral news. ❌", logging.ERROR)
            return
        
        news_processor_instance = NewsProcessor(config)
        logger.debug("NewsProcessor instance created for viral news.")

        if num_to_process is None:
            await send_msg("Processing all available viral news (iteration based)...", logging.INFO)
        
        processed_count: int = 0
        items_to_fetch: float | int = float('inf') if num_to_process is None else num_to_process
        
        while processed_count < items_to_fetch:
            news_item: Optional[Dict[str, Any]] = news_processor_instance.get_next_viral_news()
            if not news_item:
                if items_to_fetch == float('inf'): # Only log "no more" if we intended to process all available
                    await send_msg("No more viral news to process at the moment.", logging.INFO)
                break

            title: str = news_item.get('title', 'N/A')
            url: Optional[str] = news_item.get('url')
            virality_score: float = news_item.get('virality_score', 0.0)

            logger.info(f"Found viral news: Title: {title}, URL: {url}, Score: {virality_score:.2f}")

            if not url or is_url_processed(url): # Ensure URL exists before logging skip
                logger.info(f"Skipping already processed or invalid URL: {url if url else 'N/A'}")
                continue

            try:
                await send_msg(f"Processing viral news (short format): {title}...", logging.INFO)
                # The original logic used the URL as the title for processing in this specific headless flow.
                response_data: Dict[str, Any] = self.process_short_news(news_item_title=url, news_item_description="") 
                
                await send_msg(f"Successfully processed: {title}. Video ID: {response_data.get('id', 'N/A')}", logging.INFO)
                
                save_processed_news(news_item) 
                processed_count += 1
            except Exception as e:
                error_msg_user: str = f"Error processing news from URL {url}: An unexpected issue occurred. ❌"
                logger.error(f"Error processing URL {url} in viral news loop: {e}", exc_info=True)
                await send_msg(error_msg_user, logging.ERROR)
                await send_msg("Reinstating video processor (Note: processor is per-call, this is a conceptual retry path).", logging.WARNING)
                continue 

        if processed_count > 0:
            await send_msg(f"Successfully processed {processed_count} viral news item(s)! 🎉", logging.INFO)
        elif items_to_fetch > 0 and items_to_fetch != float('inf'): 
            await send_msg("No new viral news items were processed in this run.", logging.INFO)
        elif items_to_fetch == float('inf') and processed_count == 0: 
             await send_msg("No new viral news items were processed in this run.", logging.INFO)


if __name__ == '__main__':
    # Basic logging configuration for standalone execution
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    video_service = VideoService()

    # Example for short news (sync) - conceptual, actual call needs a Telegram environment or extensive mocking
    # try:
    #     logger.info("Attempting to process short news (example)...")
    #     # mock_callback_query = MagicMock(spec=CallbackQuery) # If needed
    #     # short_news_result = video_service.process_short_news("Test Title", "Test Description", mock_callback_query)
    #     # logger.info(f"Short news processing result: {short_news_result}")
    # except Exception as e:
    #     logger.error(f"Error in short news example: {e}", exc_info=True)


    # Example for viral news (async)
    async def mock_message_callback_example(text: str) -> None:
        logger.info(f"Message to user (mock_message_callback_example): {text}")

    async def demo_viral_news():
        logger.info("\n--- Viral News Processing Demo ---")
        dummy_config_path = 'dummy_config_viral_test.json'
        dummy_config_content = {"newsapi_key": "YOUR_NEWSAPI_KEY", "currentsapi_key": "YOUR_CURRENTSAPI_KEY", "other_settings": "test"}
        try:
            with open(dummy_config_path, 'w', encoding='utf-8') as f:
                json.dump(dummy_config_content, f)
            logger.debug(f"Dummy config file created: {dummy_config_path}")
            
            # Ensure NewsProcessor and its dependencies (like API clients) are either mocked 
            # or can run in a limited way for this demo.
            # Full execution of process_viral_news is complex for a simple __main__ block.
            # await video_service.process_viral_news(num_to_process=1, 
            #                                       message_callback=mock_message_callback_example, 
            #                                       config_file_path=dummy_config_path)
            logger.info("Viral news processing demo call (process_viral_news) commented out to avoid complex setup for unit test.")
            logger.info("To test fully, ensure NewsProcessor and its dependencies are set up and config file is valid.")
        except Exception as e:
            logger.error(f"Error in demo_viral_news: {e}", exc_info=True)
        finally:
            import os # Import here to keep it local to __main__
            if os.path.exists(dummy_config_path):
                os.remove(dummy_config_path)
                logger.debug(f"Dummy config file removed: {dummy_config_path}")

    # import asyncio # Not needed if demo_viral_news is not run
    # asyncio.run(demo_viral_news())
    logger.info("Standalone execution of video_service.py finished. Viral news demo not run by default.")
