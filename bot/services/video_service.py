import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from telegram import Bot, CallbackQuery

from news_video_processor import NewsVideoProcessor
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news
from scripts.factory import PipelineFactory
from scripts.utils.app_logger import trace

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_ERRORS = 3
PROCESSING_TIMEOUT = 600  # seconds (10 min) for full pipeline


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
        bot: Optional[Bot] = None,
    ) -> Optional[Dict[str, Any]]:
        logger.info("Processing short news - Title: %s", news_item_title)

        loop = asyncio.get_running_loop()
        if bot is None and callback_query is not None and hasattr(callback_query, "get_bot"):
            try:
                bot = callback_query.get_bot()
            except Exception:
                bot = None

        def _sync_run() -> Optional[Dict[str, Any]]:
            processor = NewsVideoProcessor(
                callback_query=callback_query,
                event_loop=loop,
                bot=bot,
            )
            news_data = {"title": news_item_title, "description": news_item_description}
            return processor.process_latest_news_in_short_format(news_data)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_run),
                timeout=PROCESSING_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Short news processing timed out after %ds: %s", PROCESSING_TIMEOUT, news_item_title)
            return None

    @trace()
    async def process_long_news(
        self,
        news_item_title: str,
        news_item_description: str,
        callback_query: Optional[CallbackQuery] = None,
        bot: Optional[Bot] = None,
    ) -> Optional[Dict[str, Any]]:
        logger.info("Processing long news - Title: %s", news_item_title)

        loop = asyncio.get_running_loop()
        if bot is None and callback_query is not None and hasattr(callback_query, "get_bot"):
            try:
                bot = callback_query.get_bot()
            except Exception:
                bot = None

        def _sync_run() -> Optional[Dict[str, Any]]:
            processor = NewsVideoProcessor(
                callback_query=callback_query,
                event_loop=loop,
                bot=bot,
            )
            news_data = {"title": news_item_title, "description": news_item_description}
            return processor.process_latest_news_in_long_format(news_data)

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_run),
                timeout=PROCESSING_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Long news processing timed out after %ds: %s", PROCESSING_TIMEOUT, news_item_title)
            return None

    @trace()
    async def process_url_short(
        self,
        url: str,
        callback_query: Optional[CallbackQuery] = None,
        config_path: str = "settings.json",
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> str:
        logger.info("Processing URL short - URL: %s", url)
        return await self._run_pipeline(url, "short", config_path, progress_callback)

    @trace()
    async def process_url_long(
        self,
        url: str,
        callback_query: Optional[CallbackQuery] = None,
        config_path: str = "settings.json",
        progress_callback: Optional[Callable[[Dict], None]] = None,
    ) -> str:
        logger.info("Processing URL long - URL: %s", url)
        return await self._run_pipeline(url, "long", config_path, progress_callback)

    async def _run_pipeline(
        self, url: str, fmt: str, config_path: str,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> str:
        def _sync_run() -> str:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            factory = PipelineFactory()
            pipeline = factory.create_pipeline_from_config(
                config, pipeline_type=fmt, skip_validation=True,
                progress_callback=progress_callback
            )
            return pipeline.execute({"url": url})

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_run),
                timeout=PROCESSING_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("URL pipeline timed out after %ds: %s", PROCESSING_TIMEOUT, url)
            raise

    @staticmethod
    async def _check_url_processed(url: str) -> bool:
        return await asyncio.to_thread(is_url_processed, url)

    @staticmethod
    async def _save_processed(news_data: Dict) -> None:
        await asyncio.to_thread(save_processed_news, news_data)

    @trace()
    async def process_viral_news(
        self,
        num_to_process: Optional[int] = None,
        message_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        config_file_path: str = "settings.json",
    ) -> None:
        logger.info(
            "Starting process_viral_news. Number to process: %s",
            num_to_process if num_to_process else "all",
        )

        async def send_msg(text: str, level: int = logging.INFO) -> None:
            if message_callback:
                await message_callback(text)
            logger.log(level, "ViralNewsProcessing: %s", text)

        try:
            config = await asyncio.to_thread(
                lambda: json.load(open(config_file_path, "r", encoding="utf-8"))
            )
        except FileNotFoundError:
            logger.error("Configuration file '%s' not found for viral news.", config_file_path)
            await send_msg(
                f"Error: Configuration file '{config_file_path}' not found.",
                logging.ERROR,
            )
            return
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from '%s'.", config_file_path)
            await send_msg(
                f"Error: Could not decode JSON from '{config_file_path}'.",
                logging.ERROR,
            )
            return

        news_processor_instance = NewsProcessor(config)

        if num_to_process is None:
            await send_msg("Processing all available viral news (iteration based)...")

        processed_count = 0
        consecutive_errors = 0
        items_to_fetch = float("inf") if num_to_process is None else num_to_process

        while processed_count < items_to_fetch:
            news_item = news_processor_instance.get_next_viral_news()
            if not news_item:
                if items_to_fetch == float("inf"):
                    await send_msg(
                        "No more viral news to process at the moment."
                    )
                break

            title = news_item.get("title", "N/A")
            url = news_item.get("url", "")
            logger.info("Found viral news: Title: %s, URL: %s", title, url)

            if not url or await self._check_url_processed(url):
                logger.info("Skipping already processed or invalid URL: %s", url or "N/A")
                continue

            try:
                await send_msg(f"Processing viral news (short format): {title}...")
                result = await self.process_short_news(
                    news_item_title=url,
                    news_item_description="",
                )
                if result is None:
                    raise RuntimeError("Processing returned no result")

                video_id = result.get("id", "N/A") if result else "N/A"
                await send_msg(
                    f"Successfully processed: {title}. Video ID: {video_id}" if video_id != "N/A"
                    else f"Successfully processed: {title}."
                )

                await self._save_processed(news_item)
                processed_count += 1
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    "Error processing URL %s (consecutive errors: %d): %s",
                    url, consecutive_errors, e,
                )
                await send_msg(
                    f"Error processing news from URL {url}: {e}",
                    logging.ERROR,
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    await send_msg(
                        "Too many consecutive errors. Stopping viral processing.",
                        logging.ERROR,
                    )
                    break

        if processed_count > 0:
            await send_msg(
                f"Successfully processed {processed_count} viral news item(s)!"
            )
        elif items_to_fetch > 0 and items_to_fetch != float("inf"):
            await send_msg("No new viral news items were processed in this run.")
