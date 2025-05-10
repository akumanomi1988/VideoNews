import asyncio
import json
import os
import time
import nest_asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackContext,
    CallbackQueryHandler, MessageHandler, filters
)
from scripts.DataFetcher.news_api_client import NewsAPIProvider
from scripts.DataFetcher.currents_api_client import CurrentsAPIProvider
from scripts.DataFetcher.news_aggregator import NewsAggregator
from scripts.DataFetcher.viral_news_agent import NewsProcessor
from news_video_processor import NewsVideoProcessor
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news

nest_asyncio.apply()

# Initialize news cache
news_cache = {
    "timestamp": 0,  # Last update time
    "news": []       # Cached news list
}
CACHE_TIMEOUT = 300  # 5 minutes (300 seconds)
SETTINGS_FILE = 'settings.json'

def load_settings():
    """Load settings from the JSON file."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def get_news_providers(settings):
    """Initialize news providers from settings"""
    providers = []
    if 'newsapi_key' in settings:
        providers.append(NewsAPIProvider(settings['newsapi_key']))
    if 'currentsapi_key' in settings:
        providers.append(CurrentsAPIProvider(settings['currentsapi_key']))
    return providers

async def refresh_news_cache(context: CallbackContext):
    """Refresh the news cache if needed"""
    global news_cache
    current_time = time.time()
    
    if current_time - news_cache["timestamp"] > CACHE_TIMEOUT:
        settings = load_settings()
        providers = get_news_providers(settings)
        
        if not providers:
            return False
            
        aggregator = NewsAggregator(
            providers=providers,
            config=settings
        )
        
        try:
            viral_news = aggregator.get_viral_news(
                category='technology',
                limit=settings.get('news_limit', 20),
                min_virality_score=settings.get('virality_threshold', 0.5)
            )
            
            news_cache["news"] = viral_news
            news_cache["timestamp"] = current_time
            return True
            
        except Exception as e:
            await context.bot.send_message(
                chat_id=context.user_data['chat_id'],
                text=f"Error refreshing news: {str(e)}"
            )
            return False
    
    return True

async def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    welcome_message = (
        "👋 ¡Bienvenido al Bot de Noticias Virales!\n\n"
        "Este bot te ayuda a encontrar y procesar noticias virales para crear contenido.\n\n"
        "Comandos disponibles:\n"
        "/start - Mostrar este mensaje\n"
        "/news - Ver últimas noticias virales\n"
        "/settings - Configurar el bot\n"
        "/help - Ver ayuda detallada"
    )
    await update.message.reply_text(welcome_message)

async def show_news(update: Update, context: CallbackContext):
    """Handle /news command"""
    if not await refresh_news_cache(context):
        await update.message.reply_text("❌ Error obteniendo noticias. Por favor, verifica la configuración.")
        return
        
    if not news_cache["news"]:
        await update.message.reply_text("❌ No hay noticias disponibles en este momento.")
        return
        
    context.user_data['chat_id'] = update.effective_chat.id
    
    # Crear botones para cada noticia
    keyboard = []
    for i, news in enumerate(news_cache["news"]):
        virality = news.get('virality_score', 0)
        button_text = f"📰 {news['title'][:50]}... ({virality:.2f})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"news_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔍 Selecciona una noticia para procesar:",
        reply_markup=reply_markup
    )

async def news_selection_handler(update: Update, context: CallbackContext):
    """Handle news selection"""
    query = update.callback_query
    await query.answer()
    
    try:
        news_index = int(query.data.split('_')[1])
        selected_news = news_cache["news"][news_index]
        
        # Verificar si ya fue procesada
        if is_url_processed(selected_news['url']):
            await query.message.reply_text("⚠️ Esta noticia ya fue procesada anteriormente.")
            return
            
        # Crear botones para elegir el tipo de video
        keyboard = [
            [
                InlineKeyboardButton("📱 Video Corto", callback_data=f"type_short_{news_index}"),
                InlineKeyboardButton("🎬 Video Largo", callback_data=f"type_long_{news_index}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"🎥 Selecciona el tipo de video para:\n{selected_news['title']}",
            reply_markup=reply_markup
        )
        
    except (IndexError, ValueError) as e:
        await query.message.reply_text(f"❌ Error seleccionando la noticia: {str(e)}")

async def process_video_type(update: Update, context: CallbackContext):
    """Handle video type selection"""
    query = update.callback_query
    await query.answer()
    
    try:
        video_type, news_index = query.data.split('_')[1:3]
        news_index = int(news_index)
        selected_news = news_cache["news"][news_index]
        
        await query.message.reply_text(f"🔄 Procesando noticia como video {video_type}...")
        
        processor = NewsVideoProcessor(config_file='settings.json', callback_query=query)
        
        if video_type == 'short':
            response = processor.process_latest_news_in_short_format(selected_news)
        else:
            response = processor.process_latest_news_in_long_format(selected_news)
            
        # Guardar la noticia como procesada
        save_processed_news(selected_news)
        
        await query.message.reply_text(
            f"✅ Video generado exitosamente!\n\n"
            f"Título: {selected_news['title']}\n"
            f"URL: {response}"
        )
        
    except Exception as e:
        await query.message.reply_text(f"❌ Error procesando el video: {str(e)}")
    finally:
        context.user_data.pop('news_type', None)

def main():
    """Main function to run the bot"""
    settings = load_settings()
    if 'telegram_token' not in settings:
        print("❌ Error: No se encontró el token de Telegram en la configuración")
        return
        
    app = ApplicationBuilder().token(settings['telegram_token']).build()
    
    # Registrar handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", show_news))
    app.add_handler(CallbackQueryHandler(news_selection_handler, pattern="^news_"))
    app.add_handler(CallbackQueryHandler(process_video_type, pattern="^type_"))
    
    # Iniciar el bot
    print("✅ Bot iniciado correctamente")
    app.run_polling()