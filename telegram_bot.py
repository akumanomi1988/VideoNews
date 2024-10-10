import json
import time
import nest_asyncio
from scripts.DataFetcher.news_api_client import NewsAPIClient
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, filters
)
from news_video_processor import NewsVideoProcessor

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
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
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
    keyboard.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_config')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Ask user to select a category
    await update.message.reply_text(
        "Please select a category to modify or cancel:",
        reply_markup=reply_markup
    )

# Handle category selection
async def category_selection_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_config':
        await query.message.reply_text("Configuration selection cancelled. ✅")
        return

    selected_category = query.data  # Get selected category
    settings = load_settings()
    
    # Show settings for the selected category
    category_settings = settings[selected_category]
    response = f"Configuration for *{selected_category.capitalize()}*:\n"
    
    for key in category_settings.keys():
        response += f"- {key}\n"

    response += "\nSelect a setting to modify or cancel."

    # Create inline keyboard for settings
    keyboard = [
        [InlineKeyboardButton(key, callback_data=f"{selected_category}:{key}")] 
        for key in category_settings.keys()
    ]
    
    # Add cancel option
    keyboard.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_config')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(response, reply_markup=reply_markup)

# Handle setting selection
async def setting_selection_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_config':
        await query.message.reply_text("Configuration selection cancelled. ✅")
        return

    # Split selected data into category and setting
    selected_category, selected_setting = query.data.split(':')
    settings = load_settings()
    
    # Ask the user for a new value for the selected setting
    await query.message.reply_text(f"Current value for *{selected_setting}* is *{settings[selected_category][selected_setting]}*.\nPlease enter a new value:")

    # Store context for the next message
    context.user_data['category'] = selected_category
    context.user_data['setting'] = selected_setting

# Handle the new value entered
async def handle_new_value(update: Update, context: CallbackContext):
    if 'category' in context.user_data and 'setting' in context.user_data:
        selected_category = context.user_data['category']
        selected_setting = context.user_data['setting']
        
        # Update the setting with the new value
        settings = load_settings()
        settings[selected_category][selected_setting] = update.message.text
        save_settings(settings)

        await update.message.reply_text(f"The setting *{selected_setting}* has been updated to *{update.message.text}* ✅")
        
        # Clear user data
        context.user_data.clear()
    else:
        await update.message.reply_text("No setting selected. Please start over with /config. ❌")

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
    keyboard.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message asking the user to select a category
    await update.message.reply_text(
        "Please select a news category or cancel:",
        reply_markup=reply_markup
    )

async def category_selection_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.message.reply_text("Category selection cancelled. ✅")
        return

    selected_category = query.data  # Get the selected category
    settings = load_settings()
    news_client = NewsAPIClient(api_key=settings['newsapi']['api_key'])
    
    await query.message.reply_text(f"Fetching the latest news in category: {selected_category}... 📰")

    # If the cache has expired or is empty, fetch new news
    # if not news_cache["news"] or is_cache_expired():
    latest_news = news_client.get_latest_headlines(
        country=settings['newsapi']['country'],
        page_size=settings['newsapi']['page_size'],
        category=selected_category  # Use the selected category
    )

    news_cache["news"] = latest_news  # Store in cache
    news_cache["timestamp"] = time.time()  # Update cache timestamp
    print("News cache updated.")
    # # else:
    #     latest_news = news_cache["news"]  # Use cached news
    #     print("Using cached news.")

    # Build an inline keyboard with each headline and the cancel option
    keyboard = [
        [InlineKeyboardButton(news_item['title'], callback_data=str(index))] 
        for index, news_item in enumerate(latest_news)
    ]
    
    # Add the cancel option
    keyboard.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_selection')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message with the list of news and an inline keyboard
    await query.message.reply_text(
        "Select a news item to process or cancel:",
        reply_markup=reply_markup
    )

async def news_selection_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_selection':
        await query.message.reply_text("News selection cancelled. ✅")
        return

    # Get the index of the selected news
    selected_index = int(query.data)
    
    # Load cached news
    latest_news = news_cache["news"]
    selected_news = latest_news[selected_index]  # The selected news

    # Process the selected news using the existing function
    processor = NewsVideoProcessor(progress_callback=query.message.reply_text)

    await query.message.reply_text(f"Processing news... ⏳")

    response = processor.process_latest_news_in_short_format(selected_news)  # Pass the selected news
    
    await query.message.reply_text(f"News processing completed: {format_youtube_message(response)} ✅")
    
def format_youtube_message(response):
    # Extract relevant data from the response
    title = response['snippet']['title']
    description = response['snippet']['description']
    channel = response['snippet']['channelTitle']
    published_at = response['snippet']['publishedAt']
    video_id = response['id']
    url_video = f"https://www.youtube.com/watch?v={video_id}"
    thumbnail_url = response['snippet']['thumbnails']['default']['url']

    # Format the message for Telegram
    message = f"""
        🛢️ **Title:** {title}

        📄 **Description:** {description}

        📺 **Channel:** {channel}

        📅 **Published At:** {published_at}

        🔗 **Video Link:** [Watch Video]({url_video})

        📸 ![Thumbnail]({thumbnail_url})
        """
    return message
# Function to list available settings
async def list_settings(update: Update, context: CallbackContext):
    settings = load_settings()  # Load settings from file
    response = "Available settings:\n\n"
    
    # Iterate through sections and their settings
    for section, config in settings.items():
        response += f"*{section}*\n"
        for key in config.keys():
            response += f"  - {key}\n"
        response += "\n"
    
    await update.message.reply_text(response)

async def error_handler(update: Update, context: CallbackContext):
    # Log the error
    print(f"Error: {context.error}")

    # Send a message to the user if the error occurs in a message context
    if update:
        await update.message.reply_text("An error occurred while processing your request. Please try again later. ❌")

if __name__ == '__main__':
    # Load Telegram bot token from settings.json
    settings = load_settings()
    telegram_token = settings['telegram']['bot_token']

    application = ApplicationBuilder().token(telegram_token).build()

    # Commands for configuring settings
    application.add_handler(CommandHandler("config", configure_setting))
    application.add_handler(CallbackQueryHandler(category_selection_handler, pattern='^(business|entertainment|general|health|science|sports|technology|cancel_config)$'))
    application.add_handler(CallbackQueryHandler(setting_selection_handler, pattern='^.+:.+$'))  # For selected settings
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_value))

    # Command to list available settings
    application.add_handler(CommandHandler("list_settings", list_settings))

    # Command to show news categories
    application.add_handler(CommandHandler("shortnews", show_category_selection))
    application.add_handler(CallbackQueryHandler(news_selection_handler, pattern='^[0-9]+|cancel_selection$'))

    # Add the error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling()
