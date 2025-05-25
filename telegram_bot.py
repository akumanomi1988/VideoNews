import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import nest_asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, filters
)

from scripts.DataFetcher.news_api_client import NewsAPIClient
from news_video_processor import NewsVideoProcessor
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news

nest_asyncio.apply()

# --- Constants and Configurations ---
CACHE_TIMEOUT: int = 300  # 5 minutes
SETTINGS_FILE: str = 'settings.json'
CONFIG_FILE: str = 'config.json'
NEWS_CATEGORIES: List[str] = [
    'business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology'
]

# --- Global Cache ---
news_cache: Dict[str, Any] = {
    "timestamp": 0,
    "news": []
}

# --- Utility Functions ---

def load_settings() -> Dict[str, Any]:
    """Load settings from the JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        print("Configuration file not found. Please create one using the configuration editor.")
        return {}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def is_cache_expired() -> bool:
    """Check if the news cache is expired."""
    return time.time() - news_cache["timestamp"] > CACHE_TIMEOUT

def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive configuration values."""
    sensitive_keywords = ['token', 'key', 'secret', 'password', 'credential']
    if any(s in key.lower() for s in sensitive_keywords):
        return '••••••••'
    return value

def format_youtube_message(response: Dict[str, Any]) -> str:
    """Format the YouTube upload response for Telegram."""
    snippet = response.get('snippet', {})
    title = snippet.get('title', '')
    description = snippet.get('description', '')
    channel = snippet.get('channelTitle', '')
    published_at = snippet.get('publishedAt', '')
    video_id = response.get('id', '')
    url_video = f"https://www.youtube.com/watch?v={video_id}"
    # Truncate description if too long
    description = description[:150] + "..." if len(description) > 150 else description

    return (
        "🎬 *New Video Created*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 *Title:* `{title}`\n\n"
        "📝 *Description:*\n"
        f"_{description}_\n\n"
        "🎯 *Details:*\n"
        f"• *Channel:* `{channel}`\n"
        f"• *Published:* `{published_at}`\n\n"
        f"🔗 *Watch Now:* [Open on YouTube]({url_video})\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )

def build_inline_keyboard(options: List[str], cancel_callback: str, capitalize: bool = True) -> InlineKeyboardMarkup:
    """Build an inline keyboard with options and a cancel button."""
    keyboard = [
        [InlineKeyboardButton(opt.capitalize() if capitalize else opt, callback_data=opt)]
        for opt in options
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)])
    return InlineKeyboardMarkup(keyboard)

# --- Telegram Command Handlers ---

async def configure_setting(update: Update, context: CallbackContext) -> None:
    """Start the configuration process by showing available categories."""
    settings = load_settings()
    categories = list(settings.keys())
    reply_markup = build_inline_keyboard(categories, cancel_callback='cancel_config')
    await update.message.reply_text(
        "⚙️ *Configuration Settings*\n\n"
        "Select a category to modify:\n"
        "_Choose from the options below_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_category_selection(update: Update, context: CallbackContext) -> None:
    """Handle the selection of a news category."""
    query = update.callback_query
    await query.answer()
    if query.data == 'cancel':
        await query.message.reply_text(
            "❌ *Operation Cancelled*\n"
            "News category selection cancelled.\n"
            "_Use /news_category to start again_",
            parse_mode='Markdown'
        )
        return

    selected_category = query.data
    settings = load_settings()
    news_client = NewsAPIClient(api_key=settings['newsapi']['api_key'])

    await query.message.reply_text(
        f"🔍 *Fetching News*\n\n"
        f"Category: `{selected_category.capitalize()}`\n"
        "_Please wait while I fetch the latest articles..._",
        parse_mode='Markdown'
    )

    if not news_cache["news"] or is_cache_expired():
        latest_news = news_client.get_latest_headlines(
            country=settings['newsapi']['country'],
            page_size=settings['newsapi']['page_size'],
            category=selected_category
        )
        news_cache["news"] = latest_news
        news_cache["timestamp"] = time.time()
    else:
        latest_news = news_cache["news"]

    keyboard = [
        [InlineKeyboardButton(
            news_item['title'][:100] + "..." if len(news_item['title']) > 100 else news_item['title'],
            callback_data=str(index)
        )]
        for index, news_item in enumerate(latest_news)
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_selection')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "📰 *Available News Articles*\n\n"
        "_Select an article to process:_\n"
        "Articles will be converted to video format\n"
        "with voiceover and background music.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_setting_selection(update: Update, context: CallbackContext) -> None:
    """Handle the selection of a specific setting to modify."""
    query = update.callback_query
    await query.answer()
    if query.data == 'cancel_config':
        await query.message.reply_text(
            "❌ *Configuration Cancelled*\n"
            "_Use /settings to start again_",
            parse_mode='Markdown'
        )
        return

    selected_category, selected_setting = query.data.split(':')
    settings = load_settings()
    current_value = settings[selected_category][selected_setting]

    await query.message.reply_text(
        f"🔧 *Modify Setting*\n\n"
        f"Category: `{selected_category}`\n"
        f"Setting: `{selected_setting}`\n"
        f"Current Value: `{current_value}`\n\n"
        "_Enter the new value below:_",
        parse_mode='Markdown'
    )

    context.user_data['category'] = selected_category
    context.user_data['setting'] = selected_setting

async def handle_new_value(update: Update, context: CallbackContext) -> None:
    """Handle the new value entered for a setting."""
    if 'category' in context.user_data and 'setting' in context.user_data:
        selected_category = context.user_data['category']
        selected_setting = context.user_data['setting']
        new_value = update.message.text
        settings = load_settings()
        old_value = settings[selected_category][selected_setting]
        settings[selected_category][selected_setting] = new_value
        save_settings(settings)

        await update.message.reply_text(
            "✅ *Setting Updated*\n\n"
            f"Category: `{selected_category}`\n"
            f"Setting: `{selected_setting}`\n"
            f"Old Value: `{old_value}`\n"
            f"New Value: `{new_value}`",
            parse_mode='Markdown'
        )
        context.user_data.clear()
    else:
        await update.message.reply_text(
            "❌ *Error*\n\n"
            "No setting selected.\n"
            "_Use /settings to start the configuration process._",
            parse_mode='Markdown'
        )

async def show_category_selection(update: Update, context: CallbackContext) -> None:
    """Show available news categories for selection."""
    reply_markup = build_inline_keyboard(NEWS_CATEGORIES, cancel_callback='cancel')
    await update.message.reply_text(
        "📰 *Select News Category*\n\n"
        "Choose a category for your news content:\n"
        "_Select from the options below_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_news_selection(update: Update, context: CallbackContext) -> None:
    """Handle the selection of a news article to process."""
    query = update.callback_query
    await query.answer()
    if query.data == 'cancel_selection':
        await query.message.reply_text(
            "❌ *Selection Cancelled*\n"
            "_Use /news_category to start again_",
            parse_mode='Markdown'
        )
        return

    selected_index = int(query.data)
    latest_news = news_cache["news"]
    selected_news = latest_news[selected_index]
    processor = NewsVideoProcessor(callback_query=query)

    try:
        news_type = context.user_data.get('news_type')
        if news_type == 'long':
            await query.message.reply_text(
                "🎥 *Creating Long-Format Video*\n\n"
                f"Article: `{selected_news['title'][:50]}...`\n"
                "_This may take a few minutes..._",
                parse_mode='Markdown'
            )
            response = processor.process_latest_news_in_long_format(selected_news)
        else:
            await query.message.reply_text(
                "📱 *Creating Short-Format Video*\n\n"
                f"Article: `{selected_news['title'][:50]}...`\n"
                "_This may take a few minutes..._",
                parse_mode='Markdown'
            )
            response = processor.process_latest_news_in_short_format(selected_news)

        await query.message.reply_text(
            format_youtube_message(response),
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.message.reply_text(
            "❌ *Processing Error*\n\n"
            f"Failed to process article:\n"
            f"`{selected_news['title']}`\n\n"
            f"Error: _{str(e)}_",
            parse_mode='Markdown'
        )
    finally:
        context.user_data.pop('news_type', None)

async def list_settings(update: Update, context: CallbackContext) -> None:
    """List all current settings."""
    settings = load_settings()
    if not settings:
        await update.message.reply_text(
            "⚠️ *No Settings Found*\n\n"
            "Configuration file is empty or not found.\n"
            "_Use /settings to configure the application._",
            parse_mode='Markdown'
        )
        return

    response = "⚙️ *Current Settings*\n\n"
    for section, config in settings.items():
        response += f"📁 *{section.upper()}*\n"
        for key, value in config.items():
            value = mask_sensitive_value(key, value)
            response += f"  • `{key}`: `{value}`\n"
        response += "\n"
    response += "_Use /settings to modify these values_"

    await update.message.reply_text(
        response,
        parse_mode='Markdown'
    )

async def error_handler(update: Optional[Update], context: CallbackContext) -> None:
    """Handle errors and notify the user."""
    error_message = str(context.error)
    print(f"Error detected: {error_message}")
    if "[WinError 32]" in error_message:
        if update and update.message:
            await update.message.reply_text(
                "⚠️ *System Operation Blocked*\n\n"
                "_System will retry in 2 minutes..._\n"
                "Please wait while we resolve this.",
                parse_mode='Markdown'
            )
        print("Detected file access error. Retrying in 5 seconds...")
        await asyncio.sleep(5)
        return

    if update and update.message:
        await update.message.reply_text(
            "❌ *Error Occurred*\n\n"
            "An unexpected error occurred while processing your request.\n"
            "_Please try again in a few moments._",
            parse_mode='Markdown'
        )

async def process_short_news_topic(update: Update, context: CallbackContext) -> None:
    """Process a short news video from a custom topic."""
    if context.args:
        headline = " ".join(context.args)
        await update.message.reply_text(
            "📱 *Processing Short Video*\n\n"
            f"Topic: `{headline[:50]}...`\n"
            "_Creating short-format video..._",
            parse_mode='Markdown'
        )
        try:
            processor = NewsVideoProcessor(callback_query=None)
            response = processor.process_latest_news_in_short_format({"title": headline, "description": ""})
            await update.message.reply_text(
                format_youtube_message(response),
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(
                "❌ *Processing Error*\n\n"
                f"Failed to process topic:\n"
                f"`{headline}`\n\n"
                f"Error: _{str(e)}_",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "❌ *Missing Topic*\n\n"
            "Please provide a topic or headline after the command.\n"
            "_Example: /topic_shortnews Technology advances in 2025_",
            parse_mode='Markdown'
        )

async def process_long_news_topic(update: Update, context: CallbackContext) -> None:
    """Process a long news video from a custom topic."""
    if context.args:
        headline = " ".join(context.args)
        await update.message.reply_text(
            "🎥 *Processing Long Video*\n\n"
            f"Topic: `{headline[:50]}...`\n"
            "_Creating detailed video content..._",
            parse_mode='Markdown'
        )
        try:
            processor = NewsVideoProcessor(callback_query=None)
            response = processor.process_latest_news_in_long_format({"title": headline, "description": ""})
            await update.message.reply_text(
                format_youtube_message(response),
                parse_mode='Markdown'
            )
        except Exception as e:
            await update.message.reply_text(
                "❌ *Processing Error*\n\n"
                f"Failed to process topic:\n"
                f"`{headline}`\n\n"
                f"Error: _{str(e)}_",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "❌ *Missing Topic*\n\n"
            "Please provide a topic or headline after the command.\n"
            "_Example: /topic_longnews Latest developments in AI_",
            parse_mode='Markdown'
        )

async def process_long_news(update: Update, context: CallbackContext) -> None:
    """Initiate the process for long news selection."""
    context.user_data['news_type'] = 'long'
    await show_category_selection(update, context)

async def process_headless(update: Update, context: CallbackContext) -> None:
    """Process viral news in headless mode."""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    news_processor = NewsProcessor(config)

    if not context.args:
        news_processor.process_all_news()
        await update.message.reply_text(
            "🎉 *Viral News Processing Complete*\n\n"
            "✅ All viral news items have been successfully processed!\n"
            "_Check the generated videos in your content dashboard._",
            parse_mode='Markdown'
        )
        return

    try:
        news_to_process = int(context.args[0])
        if news_to_process > 20:
            await update.message.reply_text(
                "❌ *Invalid Input*\n\n"
                "The number of news items cannot exceed 20.\n"
                "_Please provide a smaller number._",
                parse_mode='Markdown'
            )
            return

        processed_count = 0
        video_processor = NewsVideoProcessor(callback_query=update.message)

        await update.message.reply_text(
            "🔄 *Starting News Processing*\n\n"
            f"Target: `{news_to_process}` articles\n"
            "_Processing will begin momentarily..._",
            parse_mode='Markdown'
        )

        while processed_count < news_to_process:
            news_item = news_processor.get_next_viral_news()
            if not news_item:
                break

            url = news_item['url']
            if is_url_processed(url):
                continue
            try:
                youtube_response = video_processor.process_latest_news_in_long_format({"title": url, "description": ""})
                if youtube_response:
                    try:
                        await update.message.reply_text(
                            "✨ *Long Format Video Created*\n\n"
                            f"{format_youtube_message(youtube_response)}",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        await update.message.reply_text(
                            "❌ *YouTube Mapping Error*\n\n"
                            f"Error: _{str(e)}_\n\n"
                            "Continuing with next video...",
                            parse_mode='Markdown'
                        )
                short_response = video_processor.process_latest_news_in_short_format({"title": url, "description": ""})
                if short_response:
                    try:
                        youtube_response = await handle_youtube_upload(
                            update,
                            short_response['file_path'],
                            short_response['title'][:80],
                            short_response['thumbnail'],
                            short_response['description'],
                            short_response['tags']
                        )
                        await update.message.reply_text(
                            "✨ *Short Format Video Created*\n\n"
                            f"{format_youtube_message(youtube_response)}",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        await update.message.reply_text(
                            "❌ *YouTube Mapping Error*\n\n"
                            f"Error: _{str(e)}_\n\n"
                            "Continuing with next video...",
                            parse_mode='Markdown'
                        )
                save_processed_news(news_item)
                processed_count += 1

                await update.message.reply_text(
                    f"📊 *Progress Update*\n\n"
                    f"Processed: `{processed_count}/{news_to_process}`\n"
                    "_Continuing with next item..._",
                    parse_mode='Markdown'
                )

            except Exception as e:
                await update.message.reply_text(
                    "⚠️ *Processing Error*\n\n"
                    f"Failed to process article:\n"
                    f"`{url}`\n\n"
                    f"Error: _{str(e)}_",
                    parse_mode='Markdown'
                )
                await update.message.reply_text(
                    "🔄 *System Recovery*\n\n"
                    "Reinitializing processor...\n"
                    "_Please wait while we stabilize the system._",
                    parse_mode='Markdown'
                )
                video_processor = NewsVideoProcessor(callback_query=update.message)
                continue

        await update.message.reply_text(
            "🎉 *Processing Complete*\n\n"
            f"Successfully processed: `{processed_count}` articles\n"
            "_All requested news items have been converted to videos._",
            parse_mode='Markdown'
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ *System Error*\n\n"
            f"An unexpected error occurred:\n"
            f"_{str(e)}_\n\n"
            "Please try again or contact support.",
            parse_mode='Markdown'
        )

async def handle_youtube_upload(
    update: Update,
    output_file: str,
    title: str,
    cover: str,
    description: str,
    tags: List[str]
) -> Dict[str, Any]:
    """
    Handle YouTube upload with token refresh if needed.
    Returns the YouTube response dict.
    """
    try:
        youtube_response = None
        max_retries = 2
        retry_count = 0
        while retry_count < max_retries and not youtube_response:
            try:
                video_processor = NewsVideoProcessor(callback_query=None)
                upload_result = video_processor.youtube_uploader.upload(
                    output_file,
                    title=title[:80],
                    thumbnail_path=cover,
                    description=description,
                    tags=tags
                )
                # Map upload_result to the expected format for format_youtube_message
                if isinstance(upload_result, dict) and 'snippet' in upload_result and 'id' in upload_result:
                    youtube_response = upload_result
                else:
                    snippet = {
                        'title': upload_result.get('title', title),
                        'description': upload_result.get('description', description),
                        'channelTitle': upload_result.get('channelTitle', 'Unknown'),
                        'publishedAt': upload_result.get('publishedAt', ''),
                        'thumbnails': {
                            'default': {
                                'url': upload_result.get('thumbnail_url', cover)
                            }
                        }
                    }
                    video_id = upload_result.get('id') or upload_result.get('video_id') or upload_result.get('videoId')
                    youtube_response = {
                        'snippet': snippet,
                        'id': video_id or '',
                    }
                return youtube_response
            except Exception as e:
                error_str = str(e).lower()
                if ('token' in error_str and 'expired' in error_str) or 'invalid credentials' in error_str:
                    token_path = os.path.join(
                        os.path.dirname(video_processor.config['youtube']['credentials_file']),
                        'token.json'
                    )
                    if os.path.exists(token_path):
                        os.remove(token_path)
                        await update.message.reply_text(
                            "🔄 *YouTube Authentication Required*\n\n"
                            "The previous session has expired.\n"
                            "_Initializing new authentication..._",
                            parse_mode='Markdown'
                        )
                        auth_url = video_processor.youtube_uploader.get_authorization_url()
                        await update.message.reply_text(
                            "🔐 *Authentication Required*\n\n"
                            "Please authenticate with YouTube:\n"
                            f"`{auth_url}`\n\n"
                            "_Complete the authentication and then the upload will continue automatically._",
                            parse_mode='Markdown'
                        )
                        retry_count += 1
                        continue
                raise e
        if not youtube_response:
            raise Exception("Failed to authenticate with YouTube after retries")
        return youtube_response
    except Exception as e:
        await update.message.reply_text(
            "❌ *YouTube Upload Error*\n\n"
            f"Error: _{str(e)}_\n"
            "_The video was created but could not be uploaded._",
            parse_mode='Markdown'
        )
        raise e

# --- Main Application Entry Point ---

def main() -> None:
    """Main entry point for the Telegram bot."""
    settings = load_settings()
    telegram_token = settings['telegram']['bot_token']
    application = ApplicationBuilder().token(telegram_token).build()

    # Settings configuration
    application.add_handler(CommandHandler("settings", configure_setting))
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern='^(business|entertainment|general|health|science|sports|technology|cancel_config)$'))
    application.add_handler(CallbackQueryHandler(handle_setting_selection, pattern='^.+:.+$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value))
    application.add_handler(CommandHandler("show_settings", list_settings))

    # News category and selection
    application.add_handler(CommandHandler("news_category", show_category_selection))
    application.add_handler(CallbackQueryHandler(handle_news_selection, pattern='^[0-9]+|cancel_selection$'))

    # Short/long news from topic
    application.add_handler(CommandHandler("topic_shortnews", process_short_news_topic))
    application.add_handler(CommandHandler("topic_longnews", process_long_news_topic))

    # Long news from category
    application.add_handler(CommandHandler("detailed_news", process_long_news))

    # Headless mode
    application.add_handler(CommandHandler("headless", process_headless))

    # Error handler
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()