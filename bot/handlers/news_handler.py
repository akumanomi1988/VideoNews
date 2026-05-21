"""
News-related command and callback query handlers for the Telegram bot.

This module contains handlers for functionalities such as:
- Showing news categories for selection.
- Handling user's category selection and fetching news.
- Handling user's selection of a specific news item for processing.
- Processing news based on a user-provided topic (short and long formats).
- Initiating the long news processing flow.
- Handling the headless mode for processing viral news.
"""
import logging 
from typing import List, Dict, Any, Optional # For type hinting
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import CallbackContext

from bot.config import (
    get_news_api_key,
    # get_news_api_country, # NewsService will use its default or what's passed
    get_news_api_page_size,
    get_tts_language
)
from bot.services.news_service import NewsService
from bot.services.video_service import VideoService
from bot.utils.message_sender import MessageSender # Added MessageSender

# Create a logger instance for this module
logger = logging.getLogger(__name__)

def get_news_service_instance() -> NewsService:
    """Helper to get a NewsService instance with current config."""
    logger.debug("Creating NewsService instance.")
    api_key: Optional[str] = get_news_api_key()
    tts_lang: str = get_tts_language()
    page_size: int = get_news_api_page_size()
    return NewsService(api_key=api_key, default_language=tts_lang, default_page_size=page_size)

def get_video_service_instance() -> VideoService:
    """Helper to get a VideoService instance."""
    logger.debug("Creating VideoService instance.")
    return VideoService()


async def show_category_selection(update: Update, context: CallbackContext) -> None:
    """
    Displays an inline keyboard with news categories for the user to select.
    This is typically triggered by the /news_category command.
    """
    logger.info("show_category_selection called.")
    message_sender = MessageSender(context=context)
    news_service = get_news_service_instance()
    categories = news_service.get_news_categories()
    keyboard = [
        [InlineKeyboardButton(category.capitalize(), callback_data=category)] 
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_news_category')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message_sender.send_message(
        update=update,
        text="Please select a news category or cancel:",
        reply_markup=reply_markup
    )

async def news_category_selection_handler(update: Update, context: CallbackContext):
    """
    Handles the user's selection of a news category from the inline keyboard.
    Fetches news for the selected category and presents a list of news items.
    """
    query: Optional[CallbackQuery] = update.callback_query
    if not query or not query.data: # Should not happen if called from CallbackQueryHandler
        logger.warning("news_category_selection_handler called without query or query.data")
        return
        
    await query.answer()
    message_sender = MessageSender(context=context)

    if query.data == 'cancel_news_category':
        logger.info("News category selection cancelled by user.")
        await message_sender.send_message(update=update, text="News category selection cancelled. ✅")
        return
        
    selected_category: str = query.data
    logger.info(f"User selected news category: {selected_category}")
    news_service = get_news_service_instance()

    if not news_service.api_key: 
        logger.warning("News API key is not configured.")
        await message_sender.send_message(update=update, text="News API key is not configured. Please set NEWS_API_KEY in the .env file. 🔑")
        return

    await message_sender.send_message(update=update, text=f"Fetching the latest news in category: {selected_category}... 📰")
    
    latest_news: List[Dict[str, Any]] = news_service.fetch_news(category=selected_category) 
        
    if not latest_news:
        logger.info(f"No news found for category: {selected_category}.")
        await message_sender.send_message(update=update, text=f"No news found for category: {selected_category}. Try again later. 😕")
        return

    keyboard_buttons: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(item.get('title', 'No Title'), callback_data=f"news_{index}")] 
        for index, item in enumerate(latest_news)
    ]
    keyboard_buttons.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_news_selection')])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await message_sender.send_message(
        update=update,
        text="Select a news item to process or cancel:",
        reply_markup=reply_markup
    )

async def news_selection_handler(update: Update, context: CallbackContext) -> None:
    """
    Handles the user's selection of a specific news item from the list.
    Processes the selected news item into a video (short or long format based on context).
    """
    query: Optional[CallbackQuery] = update.callback_query
    if not query or not query.data:
        logger.warning("news_selection_handler called without query or query.data")
        return

    await query.answer()
    message_sender = MessageSender(context=context)

    if query.data == 'cancel_news_selection':
        logger.info("News item selection cancelled by user.")
        await message_sender.send_message(update=update, text="News selection cancelled. ✅")
        return
        
    selected_index_str: str = query.data.replace("news_", "")
    try:
        selected_index: int = int(selected_index_str)
    except ValueError:
        logger.error(f"Invalid news index received: {selected_index_str}", exc_info=True)
        await message_sender.send_message(update=update, text="Invalid selection. Please try again. 🤔")
        return
        
    logger.info(f"User selected news item at index: {selected_index}")
    news_service = get_news_service_instance() 
    selected_news_item: Optional[Dict[str, Any]] = news_service.get_cached_news_item(selected_index)

    if not selected_news_item:
        logger.warning(f"Could not find cached news item at index: {selected_index}")
        await message_sender.send_message(update=update, text="Could not find the selected news item. Please try selecting a category again. 🤔")
        return
        
    video_service = get_video_service_instance()
    news_title: str = selected_news_item.get('title', 'N/A')
    news_description: str = selected_news_item.get('description', '') 

    news_type_long: bool = context.user_data.get('news_type') == 'long'
    logger.info(f"Processing news item: '{news_title}' as {'long' if news_type_long else 'short'} format.")

    try:
        response_data: Dict[str, Any] # Define type for response
        if news_type_long:
            await message_sender.send_message(update=update, text=f"Processing long news: {news_title}... ⏳")
            response_data = video_service.process_long_news(
                news_item_title=news_title,
                news_item_description=news_description,
                callback_query=query 
            )
        else:
            await message_sender.send_message(update=update, text=f"Processing short news: {news_title}... ⏳")
            response_data = video_service.process_short_news(
                news_item_title=news_title,
                news_item_description=news_description,
                callback_query=query
            )
        logger.info(f"Successfully processed news item: '{news_title}'")
        await message_sender.send_message(update=update, text=f"News processing completed: {format_youtube_message(response_data)} ✅")
    except Exception as e:
        logger.error(f"Error processing news item '{news_title}': {e}", exc_info=True)
        await message_sender.send_message(update=update, text=f"An error occurred while processing the news '{news_title}': {str(e)}. ❌")
    finally:
        context.user_data.pop('news_type', None)

def format_youtube_message(response: Optional[Dict[str, Any]]) -> str:
    """
    Formats the YouTube video information from a dictionary into a
    human-readable string for a Telegram message.

    Args:
        response: A dictionary containing video details, typically from
                  a video processing service. Expected to have 'snippet'
                  and 'id' keys if valid.

    Returns:
        A formatted string message or an error message if formatting fails.
    """
    if not isinstance(response, dict) or 'snippet' not in response or 'id' not in response:
        logger.warning(f"Invalid response structure for formatting YouTube message: {response}")
        return "Could not format YouTube message: Invalid or empty response structure from video processing."
    
    snippet: Dict[str, Any] = response.get('snippet', {})
    title: str = snippet.get('title', 'N/A')
    description: str = str(snippet.get('description', '')) 
    channel: str = snippet.get('channelTitle', 'N/A')
    published_at: str = snippet.get('publishedAt', 'N/A')
    video_id: Optional[str] = response.get('id')
    
    if not video_id: 
        logger.warning(f"Video ID missing in response: {response}")
        return "Could not format YouTube message: Video ID missing."
        
    url_video: str = f"https://www.youtube.com/watch?v={video_id}"
    thumbnails: Dict[str, Any] = snippet.get('thumbnails', {})
    default_thumbnail: Dict[str, Any] = thumbnails.get('default', {})
    thumbnail_url: str = default_thumbnail.get('url', '')
    
    # Ensure description is not too long for Telegram message
    max_desc_length: int = 200 # Adjust as needed
    if len(description) > max_desc_length:
        description = description[:max_desc_length] + "..."

    message: str = f"""
    🛢️ *Title:* {title}
    📄 *Description:* {description}
    📺 *Channel:* {channel}
    📅 *Published At:* {published_at}
    🔗 *Video Link:* [Watch Video]({url_video})
    """
    if thumbnail_url:
        message += f"\n🖼️ [Thumbnail]({thumbnail_url})" 
    return message

async def short_news_topic(update: Update, context: CallbackContext) -> None:
    """
    Handles the /topic_shortnews command.
    Processes a user-provided topic into a short news video.
    Requires context.args to contain the topic.
    """
    message_sender = MessageSender(context=context)
    if context.args:
        headline: str = " ".join(context.args)
        logger.info(f"short_news_topic called with headline: {headline}")
        await message_sender.send_message(update=update, text=f"Processing short news with headline: {headline}... 📰")
        video_service = get_video_service_instance()
        try:
            response_data: Dict[str, Any] = video_service.process_short_news(news_item_title=headline, news_item_description="")
            logger.info(f"Successfully processed short_news_topic for headline: {headline}")
            await message_sender.send_message(update=update, text=f"News processing completed: {format_youtube_message(response_data)} ✅")
        except Exception as e:
            logger.error(f"Error processing short_news_topic for headline '{headline}': {e}", exc_info=True)
            await message_sender.send_message(update=update, text=f"Sorry, an error occurred while processing the news for '{headline}'. Please try again later. 🛠️")
    else:
        logger.info("short_news_topic called without arguments.")
        await message_sender.send_message(update=update, text="Please provide a topic after the command. Usage: /topic_shortnews <your topic>")

async def long_news_topic(update: Update, context: CallbackContext) -> None:
    """
    Handles the /topic_longnews command.
    Processes a user-provided topic into a long news video.
    Requires context.args to contain the topic.
    """
    message_sender = MessageSender(context=context)
    if context.args:
        headline: str = " ".join(context.args)
        logger.info(f"long_news_topic called with headline: {headline}")
        await message_sender.send_message(update=update, text=f"Processing long news with headline: {headline}... ⏳")
        video_service = get_video_service_instance()
        try:
            response_data: Dict[str, Any] = video_service.process_long_news(news_item_title=headline, news_item_description="")
            logger.info(f"Successfully processed long_news_topic for headline: {headline}")
            await message_sender.send_message(update=update, text=f"Long news processing completed: {format_youtube_message(response_data)} ✅")
        except Exception as e:
            logger.error(f"Error processing long_news_topic for headline '{headline}': {e}", exc_info=True)
            await message_sender.send_message(update=update, text=f"Sorry, an error occurred while processing the news for '{headline}'. Please try again later. 🛠️")
    else:
        logger.info("long_news_topic called without arguments.")
        await message_sender.send_message(update=update, text="Please provide a topic after the command. Usage: /topic_longnews <your topic>")

async def long_news(update: Update, context: CallbackContext) -> None:
    """
    Handles the /detailed_news command.
    Initiates the process for creating a long-form news video by first
    showing news category selection to the user. Sets 'news_type' in
    user_data to 'long'.
    """
    logger.info("long_news called, setting news_type to 'long'.")
    context.user_data['news_type'] = 'long' # type: ignore[attr-defined] # context.user_data is dict-like
    await show_category_selection(update, context) 

async def headless(update: Update, context: CallbackContext) -> None:
    """
    Handles the /headless command for processing viral news.
    Optionally accepts a number of articles to process.
    This command's execution involves interactions with VideoService.
    """
    logger.info("headless command called.")
    message_sender = MessageSender(context=context) 
    video_service = get_video_service_instance()
    num_to_process_arg = context.args[0] if context.args else None
    num_to_process = None

    if num_to_process_arg:
        try:
            num_to_process = int(num_to_process_arg)
            if num_to_process > 20: 
                logger.warning(f"Headless command: User requested {num_to_process} items, which exceeds limit of 20.")
                await message_sender.send_message(update=update, text="Error: The number of news items to process cannot exceed 20. ❌")
                return
            if num_to_process <= 0:
                logger.warning(f"Headless command: User requested non-positive number of items: {num_to_process}.")
                await message_sender.send_message(update=update, text="Error: Number of news items must be a positive integer. ➕")
                return
            logger.info(f"Headless command: Processing {num_to_process} news items.")
        except ValueError:
            logger.error(f"Headless command: Invalid argument for number of items: {num_to_process_arg}", exc_info=True)
            await message_sender.send_message(update=update, text="Error: Argument must be a number. 🔢 Usage: /headless [number_of_articles]")
            return
    else:
        # If no argument, it means process all (as per VideoService logic)
        logger.info("Headless command: Processing all available news items (no specific number provided).")
    
    async def service_message_callback(text: str):
        await message_sender.send_message(update=update, text=text) 

    await message_sender.send_message(update=update, text=f"Starting headless processing for {num_to_process if num_to_process else 'all available'} news items... 🤖")
    
    try:
        await video_service.process_viral_news(
            num_to_process=num_to_process, 
            message_callback=service_message_callback 
        )
        logger.info("Headless processing completed successfully via handler.")
    except Exception as e:
        logger.error(f"Unexpected error during headless command execution via handler: {e}", exc_info=True)
        await message_sender.send_message(update=update, text="An unexpected error occurred during headless processing. Please check logs. 🛠️")
