import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable

from telegram import CallbackQuery

from news_video_processor import NewsVideoProcessor
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news
from scripts.factory import PipelineFactory
from scripts.utils.app_logger import trace

logger = logging.getLogger(__name__)


class VideoService:

    @trace()
    def __init__(self) -> None:
        logger.debug("VideoService initialized.")

    @trace()
    async def process_short_news(
        self,
        news_item_title: str,
        news_item_description: str,
        callback_query: Optional[CallbackQuery] = None,
    ) -> Dict[str, Any]:
        """FLUJO A: process news TITLE into short video via legacy NewsVideoProcessor (async wrapper)"""
        logger.info(f"Processing short news - Title: {news_item_title}")

        def _sync_run() -> Dict[str, Any]:
            processor = NewsVideoProcessor(callback_query=callback_query)
            news_data = {"title": news_item_title, "description": news_item_description}
            return processor.process_latest_news_in_short_format(news_data)

        return await asyncio.to_thread(_sync_run)

    @trace()
    async def process_long_news(
        self,
        news_item_title: str,
        news_item_description: str,
        callback_query: Optional[CallbackQuery] = None,
    ) -> Dict[str, Any]:
        """FLUJO A: process news TITLE into long video via legacy NewsVideoProcessor (async wrapper)"""
        logger.info(f"Processing long news - Title: {news_item_title}")

        def _sync_run() -> Dict[str, Any]:
            processor = NewsVideoProcessor(callback_query=callback_query)
            news_data = {"title": news_item_title, "description": news_item_description}
            return processor.process_latest_news_in_long_format(news_data)

        return await asyncio.to_thread(_sync_run)

    @trace()
    async def process_url_short(
        self,
        url: str,
        callback_query: Optional[CallbackQuery] = None,
        config_path: str = "settings.json",
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> str:
        """FLUJO B: process URL into short video via PipelineFactory"""
        logger.info(f"Processing URL short - URL: {url}")
        return await self._run_pipeline(url, "short", config_path, progress_callback)

    @trace()
    async def process_url_long(
        self,
        url: str,
        callback_query: Optional[CallbackQuery] = None,
        config_path: str = "settings.json",
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> str:
        """FLUJO B: process URL into long video via PipelineFactory"""
        logger.info(f"Processing URL long - URL: {url}")
        return await self._run_pipeline(url, "long", config_path, progress_callback)

    async def _run_pipeline(
        self, url: str, fmt: str, config_path: str,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> str:
        """Execute pipeline in thread pool to avoid blocking event loop"""
        def _sync_run() -> str:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            factory = PipelineFactory()
            pipeline = factory.create_pipeline_from_config(
                config, pipeline_type=fmt, skip_validation=True,
                progress_callback=progress_callback
            )
            result = pipeline.execute({"url": url})
            return result

        return await asyncio.to_thread(_sync_run)

    @trace()
    async def process_viral_news(
        self,
        num_to_process: Optional[int] = None,
        message_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        config_file_path: str = "settings.json",
    ) -> None:
        """Process viral news items via NewsProcessor"""
        logger.info(f"Starting process_viral_news. Number to process: {num_to_process if num_to_process else 'all'}")

        async def send_msg(text: str, level: int = logging.INFO) -> None:
            if message_callback:
                await message_callback(text)
            logger.log(level, f"ViralNewsProcessing: {text}")

        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.debug(f"Successfully loaded configuration from {config_file_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file '{config_file_path}' not found for viral news processing.", exc_info=True)
            await send_msg(f"Error: Configuration file '{config_file_path}' not found. Cannot process viral news.", logging.ERROR)
            return
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from '{config_file_path}'.", exc_info=True)
            await send_msg(f"Error: Could not decode JSON from '{config_file_path}'. Cannot process viral news.", logging.ERROR)
            return

        news_processor_instance = NewsProcessor(config)
        logger.debug("NewsProcessor instance created for viral news.")

        if num_to_process is None:
            await send_msg("Processing all available viral news (iteration based)...", logging.INFO)

        processed_count = 0
        items_to_fetch = float("inf") if num_to_process is None else num_to_process

        while processed_count < items_to_fetch:
            news_item = news_processor_instance.get_next_viral_news()
            if not news_item:
                if items_to_fetch == float("inf"):
                    await send_msg("No more viral news to process at the moment.", logging.INFO)
                break

            title = news_item.get("title", "N/A")
            url = news_item.get("url")
            logger.info(f"Found viral news: Title: {title}, URL: {url}")

            if not url or is_url_processed(url):
                logger.info(f"Skipping already processed or invalid URL: {url if url else 'N/A'}")
                continue

            try:
                await send_msg(f"Processing viral news (short format): {title}...", logging.INFO)
                response_data = await self.process_short_news(news_item_title=url, news_item_description="")

                await send_msg(f"Successfully processed: {title}. Video ID: {response_data.get('id', 'N/A')}", logging.INFO)

                save_processed_news(news_item)
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing URL {url} in viral news loop: {e}", exc_info=True)
                await send_msg(f"Error processing news from URL {url}: An unexpected issue occurred.", logging.ERROR)
                continue

        if processed_count > 0:
            await send_msg(f"Successfully processed {processed_count} viral news item(s)!", logging.INFO)
        elif items_to_fetch > 0 and items_to_fetch != float("inf"):
            await send_msg("No new viral news items were processed in this run.", logging.INFO)
        elif items_to_fetch == float("inf") and processed_count == 0:
            await send_msg("No new viral news items were processed in this run.", logging.INFO)
