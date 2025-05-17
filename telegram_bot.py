import asyncio
import json
import os
import time
import nest_asyncio
from scripts.DataFetcher.news_api_client import NewsAPIClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, filters
)
from news_video_processor import NewsVideoProcessor
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news

nest_asyncio.apply()

# Initialize news cache
news_cache = {
    "timestamp": 0,  # Last update time
    "news": []       # Cached news list
}
CACHE_TIMEOUT = 300  # 5 minutes (300 seconds)
SETTINGS_FILE = 'settings.json'

# Configuration functions
def load_settings():
    """Load settings from the JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        print("Configuration file not found. Please create one using the configuration editor.")
        return {}
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# Command to configure settings
async def configure_setting(update: Update, context: CallbackContext):
    settings = load_settings()
    categories = list(settings.keys())
    # Create inline keyboard for categories
    keyboard = [
        [InlineKeyboardButton(category.capitalize(), callback_data=category)] 
        for category in categories
    ]
    # Add cancel option
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_config')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ *Configuration Settings*\n\n"
        "Select a category to modify:\n"
        "_Choose from the options below_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Handle category selection
async def category_selection_handler(update: Update, context: CallbackContext):
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
        [InlineKeyboardButton(news_item['title'][:100] + "..." if len(news_item['title']) > 100 else news_item['title'], 
                            callback_data=str(index))] 
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

# Handle setting selection
async def setting_selection_handler(update: Update, context: CallbackContext):
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

# Handle the new value entered
async def handle_new_value(update: Update, context: CallbackContext):
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

# News functions
def is_cache_expired():
    return time.time() - news_cache["timestamp"] > CACHE_TIMEOUT

async def show_category_selection(update: Update, context: CallbackContext):
    categories = ['business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology']
    
    # Build an inline keyboard with each category and the cancel option
    keyboard = [
        [InlineKeyboardButton(category.capitalize(), callback_data=category)] 
        for category in categories
    ]
    # Add the cancel option
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send message asking the user to select a category
    await update.message.reply_text(
        "📰 *Select News Category*\n\n"
        "Choose a category for your news content:\n"
        "_Select from the options below_",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def category_selection_handler(update: Update, context: CallbackContext):
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
        [InlineKeyboardButton(news_item['title'][:100] + "..." if len(news_item['title']) > 100 else news_item['title'], 
                            callback_data=str(index))] 
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

async def news_selection_handler(update: Update, context: CallbackContext):
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
        if context.user_data.get('news_type') == 'long':
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
            f"{format_youtube_message(response)}",
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

def format_youtube_message(response):
    # Extract relevant data from the response
    title = response['snippet']['title']
    description = response['snippet']['description']
    channel = response['snippet']['channelTitle']
    published_at = response['snippet']['publishedAt']
    video_id = response['id']
    url_video = f"https://www.youtube.com/watch?v={video_id}"
    thumbnail_url = response['snippet']['thumbnails']['default']['url']

    # Truncate description if too long (keep first 150 characters)
    description = description[:150] + "..." if len(description) > 150 else description
    
    # Format the message for Telegram with improved styling
    message = f"""
🎬 *New Video Created*
━━━━━━━━━━━━━━━━━━━━━
📺 *Title:* `{title}`

📝 *Description:*
_{description}_

🎯 *Details:*
• *Channel:* `{channel}`
• *Published:* `{published_at}`

🔗 *Watch Now:* [Open on YouTube]({url_video})
━━━━━━━━━━━━━━━━━━━━━
"""
    return message

# Function to list available settings
async def list_settings(update: Update, context: CallbackContext):
    settings = load_settings()
    response = "⚙️ *Current Settings*\n\n"
    
    if not settings:
        await update.message.reply_text(
            "⚠️ *No Settings Found*\n\n"
            "Configuration file is empty or not found.\n"
            "_Use /settings to configure the application._",
            parse_mode='Markdown'
        )
        return
        
    for section, config in settings.items():
        response += f"📁 *{section.upper()}*\n"
        for key, value in config.items():
            # Mask sensitive values
            if any(sensitive in key.lower() for sensitive in ['token', 'key', 'secret', 'password', 'credential']):
                value = '••••••••'
            response += f"  • `{key}`: `{value}`\n"
        response += "\n"
    
    response += "_Use /settings to modify these values_"
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown'
    )

async def error_handler(update: Update, context: CallbackContext):
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

    # Si el error ocurre en un contexto de mensaje, informamos al usuario
    if update and update.message:
        await update.message.reply_text(
            "❌ *Error Occurred*\n\n"
            "An unexpected error occurred while processing your request.\n"
            "_Please try again in a few moments._",
            parse_mode='Markdown'
        )

# Procesa noticia corta a partir de un tema
async def short_news_topic(update: Update, context: CallbackContext):
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
                f"{format_youtube_message(response)}",
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

# Procesa noticia larga a partir de un tema
async def long_news_topic(update: Update, context: CallbackContext):
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
                f"{format_youtube_message(response)}",
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

# Procesa noticia larga seleccionando una categoría (flujo original)
async def long_news(update: Update, context: CallbackContext):
    # Almacenar en el contexto que se está buscando una noticia larga
    context.user_data['news_type'] = 'long'
    await show_category_selection(update, context)

async def headless(update: Update, context: CallbackContext):
    with open('config.json', 'r', encoding='utf-8') as f:
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
        video_processor = NewsVideoProcessor(callback_query=None)
        
        # Initial status message
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
            if is_url_processed(news_item['url']):
                continue

            try:
                # Process news in both formats
                long_response = video_processor.process_latest_news_in_long_format({"title": url, "description": ""})
                await update.message.reply_text(
                    "✨ *Long Format Video Created*\n\n"
                    f"{format_youtube_message(long_response)}",
                    parse_mode='Markdown'
                )
                
                short_response = video_processor.process_latest_news_in_short_format({"title": url, "description": ""})
                await update.message.reply_text(
                    "✨ *Short Format Video Created*\n\n"
                    f"{format_youtube_message(short_response)}",
                    parse_mode='Markdown'
                )

                save_processed_news(news_item)
                processed_count += 1

                # Progress update
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
                video_processor = NewsVideoProcessor(callback_query=None)
                continue

        # Final completion message
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


# Añadir los comandos a la aplicación
if __name__ == '__main__':
    settings = load_settings()
    telegram_token = settings['telegram']['bot_token']
    application = ApplicationBuilder().token(telegram_token).build()

    # Commands for configuring settings
    application.add_handler(CommandHandler("settings", configure_setting))
    application.add_handler(CallbackQueryHandler(category_selection_handler, pattern='^(business|entertainment|general|health|science|sports|technology|cancel_config)$'))
    application.add_handler(CallbackQueryHandler(setting_selection_handler, pattern='^.+:.+$'))  # For selected settings
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value))
    # Command to list available settings
    application.add_handler(CommandHandler("show_settings", list_settings))
    # Command to show news categories for short news
    application.add_handler(CommandHandler("news_category", show_category_selection))
    application.add_handler(CallbackQueryHandler(news_selection_handler, pattern='^[0-9]+|cancel_selection$'))
    # Command to show short news from a custom topic
    application.add_handler(CommandHandler("topic_shortnews", short_news_topic))
    # Command to show news categories for long news
    application.add_handler(CommandHandler("detailed_news", long_news))
    # Command to show long news from a custom topic
    application.add_handler(CommandHandler("topic_longnews", long_news_topic))
    # Add the new command for headless mode
    application.add_handler(CommandHandler("headless", headless))
    # Add the error handler
    application.add_error_handler(error_handler)
    # Start the bot
    application.run_polling()