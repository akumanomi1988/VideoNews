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
    if not news_cache["news"] or is_cache_expired():
        latest_news = news_client.get_latest_headlines(
            country=settings['newsapi']['country'],
            page_size=settings['newsapi']['page_size'],
            category=selected_category  # Use the selected category
        )
        news_cache["news"] = latest_news  # Store in cache
        news_cache["timestamp"] = time.time()  # Update cache timestamp
        print("News cache updated.")
    else:
        latest_news = news_cache["news"]  # Use cached news
        print("Using cached news.")
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
    # Obtener el índice de la noticia seleccionada
    selected_index = int(query.data)
    # Cargar las noticias cacheadas
    latest_news = news_cache["news"]
    selected_news = latest_news[selected_index]  # La noticia seleccionada
    # Procesar la noticia según el tipo seleccionado (corta o larga)
    processor = NewsVideoProcessor(callback_query=query)
    try:
        if context.user_data.get('news_type') == 'long':
            await query.message.reply_text(f"Processing long news... ⏳")
            response = processor.process_latest_news_in_long_format(selected_news)  # Procesar como noticia larga
        else:
            await query.message.reply_text(f"Processing short news... ⏳")
            response = processor.process_latest_news_in_short_format(selected_news)  # Procesar como noticia corta
        await query.message.reply_text(f"News processing completed: {format_youtube_message(response)} ✅")
    except Exception as e:
        await query.message.reply_text(f"An error occurred while processing the news: {str(e)}. ❌")
    finally:
        # Limpiar el tipo de noticia del contexto
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
    error_message = str(context.error)
    print(f"Error detected: {error_message}")
    if "[WinError 32]" in error_message:
        if update and update.message:
            await update.message.reply_text("System file blocked. Let's retry in 2 minutes...")
        print("Detected file access error. Retrying in 5 seconds...")
        await asyncio.sleep(5)  # Espera antes de reintentar
        return  # No reinicies la aplicación, solo reintenta
    # Si el error ocurre en un contexto de mensaje, informamos al usuario
    if update and update.message:
        await update.message.reply_text("An error occurred while processing your request. Please try again later. ❌")

# Procesa noticia corta a partir de un tema
async def short_news_topic(update: Update, context: CallbackContext):
    if context.args:
        headline = " ".join(context.args)  # Unir el argumento en caso de que sea un titular largo
        await update.message.reply_text(f"Processing short news with headline: {headline}... 📰")
        try:
            # Procesar el titular directamente como noticia corta
            processor = NewsVideoProcessor(callback_query=None)
            response = processor.process_latest_news_in_short_format({"title": headline, "description": ""})
            await update.message.reply_text(f"News processing completed: {format_youtube_message(response)} ✅")
        except Exception as e:
            await update.message.reply_text(f"An error occurred while processing the news: {str(e)}. ❌")
    else:
        await update.message.reply_text("Please provide a headline/topic after the command.")

# Procesa noticia larga a partir de un tema
async def long_news_topic(update: Update, context: CallbackContext):
    if context.args:
        headline = " ".join(context.args)  # Unir el argumento en caso de que sea un titular largo
        await update.message.reply_text(f"Processing long news with headline: {headline}... ⏳")
        try:
            # Procesar el titular directamente como noticia larga
            processor = NewsVideoProcessor(callback_query=None)
            response = processor.process_latest_news_in_long_format({"title": headline, "description": ""})
            await update.message.reply_text(f"Long news processing completed: {format_youtube_message(response)} ✅")
        except Exception as e:
            await update.message.reply_text(f"An error occurred while processing the news: {str(e)}. ❌")
    else:
        await update.message.reply_text("Please provide a headline/topic after the command.")

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
        await update.message.reply_text("All viral news processed! 🎉")
        return

    try:
        news_to_process = int(context.args[0])
        if news_to_process > 20:
            await update.message.reply_text("Error: The argument must be a number and cannot exceed 20. ❌")
            return

        processed_count = 0

        video_processor = NewsVideoProcessor(callback_query=None)
        while processed_count < news_to_process:
            news_item = news_processor.get_next_viral_news()
            if not news_item:
                break  # No hay más noticias por procesar

            print(f"Título: {news_item['title']}")
            print(f"URL: {news_item['url']}")
            print(f"Puntaje de Viralidad: {news_item['virality_score']:.2f}\n")

            url = news_item['url']
            if is_url_processed(news_item['url']):
                continue

            try:
                # Procesar noticias en formato largo y corto
                #long_response = video_processor.process_latest_news_in_long_format({"title": url, "description": ""})
                #await update.message.reply_text(f"News processing completed: {format_youtube_message(long_response)} ✅")
                
                short_response = video_processor.process_latest_news_in_short_format({"title": url, "description": ""})
                await update.message.reply_text(f"Short format created: {format_youtube_message(short_response)} ✅")

                # Marcar la noticia como procesada
                save_processed_news(news_item)
                processed_count += 1

            except Exception as e:
                # Manejar errores de procesamiento
                await update.message.reply_text(f"Error processing {url}: {str(e)} ❌")

                # Reinstanciar el `processor` para evitar estados inválidos
                await update.message.reply_text("Reinstantiating processor due to an error... 🔄")
                video_processor = NewsVideoProcessor(callback_query=None)
                continue

        await update.message.reply_text("All viral news processed! 🎉")

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)} ❌")


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