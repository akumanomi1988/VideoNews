import json
from scripts.IA.text_to_image import StylePreset,FluxImageGenerator
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler
from telegram.ext import filters
from news_video_processor import NewsVideoProcessor
import nest_asyncio

nest_asyncio.apply()

SETTINGS_FILE = 'settings.json'
# Function to load the current settings
def load_settings():
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

# Function to save the updated settings
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# Command to configure a specific setting
async def configure_setting(update: Update, context: CallbackContext):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /config [section] [setting] [value]")
        return
    
    section = context.args[0]
    setting_key = context.args[1]
    setting_value = context.args[2]
    
    settings = load_settings()
    if section in settings and setting_key in settings[section]:
        settings[section][setting_key] = setting_value
        save_settings(settings)
        await update.message.reply_text(f"Setting '{setting_key}' in section '{section}' updated to '{setting_value}'")
    else:
        await update.message.reply_text(f"Setting '{setting_key}' not found in section '{section}'.")

async def style_selection_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()  # Necesario para cerrar el botón

    selected_style = selected_style = query.data.upper()
    # Verificar si el estilo seleccionado es válido
    try:
        style_enum = StylePreset[selected_style]
        context.user_data['selected_style'] = style_enum.name  # Guarda el nombre del estilo en el contexto
        await query.edit_message_text(text=f"Has seleccionado el estilo: {style_enum.name}. Por favor, proporciona un prompt para la generación de la imagen:")
        context.user_data['awaiting_prompt'] = True
    except KeyError:
        await query.edit_message_text(text="Estilo no válido. Por favor, selecciona uno de los estilos predefinidos.")


async def prompt_handler(update: Update, context: CallbackContext):
    if context.user_data.get('awaiting_prompt'):
        user_prompt = update.message.text
        selected_style_name = context.user_data.get('selected_style', "").upper()  # Asegúrate de obtener el nombre en mayúsculas
        
        # Obtener el estilo desde StylePreset
        try:
            selected_style = StylePreset[selected_style_name]
        except KeyError:
            await update.message.reply_text("Estilo no válido. Por favor, selecciona un estilo primero usando /image.")
            return
        
        # Generar la imagen usando el prompt y el estilo seleccionado
        await update.message.reply_text(f"Generando imagen con el prompt: '{user_prompt}' y estilo: '{selected_style.name}'...")

        processor = NewsVideoProcessor(progress_callback=update.message.reply_text)

        # Llamar a fetch_related_media con el estilo correcto
        media_files = processor.fetch_related_media([user_prompt], style=selected_style,max_items=1)[0]

        # Procesar la respuesta (esto puede necesitar ajustes según cómo manejes los medios)
        if media_files:
            await update.message.reply_text("La imagen ha sido generada exitosamente.")
            await update.message.reply_document(media_files)
        else:
            await update.message.reply_text("No se encontraron medios relacionados.")

        # Limpiar el estado
        context.user_data['awaiting_prompt'] = False
        context.user_data['selected_style'] = None
    else:
        await update.message.reply_text("Por favor, selecciona un estilo primero usando /image.")

# Command to list available settings
async def list_settings(update: Update, context: CallbackContext):
    settings = load_settings()  # Load the settings from the file
    response = "Available settings:\n\n"
    
    # Iterate through sections and their settings
    for section, config in settings.items():
        response += f"*{section}*\n"
        for key in config.keys():
            response += f"  - {key}\n"
        response += "\n"
    
    await update.message.reply_text(response)

# Command to show help
async def show_help(update: Update, context: CallbackContext):
    await list_settings(update, context)

async def process_news(update: Update, context: CallbackContext):
    processor = NewsVideoProcessor(progress_callback=update.message.reply_text)
    await update.message.reply_text("Processing latest news...")
    
    response = processor.process_latest_news()
    await update.message.reply_text(f"News processing completed. {response}")

async def image_generation(update: Update, context: CallbackContext):
    # Mostrar opciones de estilo
    keyboard = [[InlineKeyboardButton(style.name, callback_data=style.name)] for style in StylePreset]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Selecciona un estilo de imagen:', reply_markup=reply_markup)

    # Almacenar el estado del usuario para recibir la opción seleccionada
    context.user_data['awaiting_style_selection'] = True

if __name__ == '__main__':
    # Load Telegram bot token from settings.json
    settings = load_settings()
    telegram_token = settings['telegram']['bot_token']

    application = ApplicationBuilder().token(telegram_token).build()

    # Command to configure settings
    application.add_handler(CommandHandler("config", configure_setting))

    # Command to execute the application
    application.add_handler(CommandHandler("execute", process_news))

    # Command to list available settings
    application.add_handler(CommandHandler("list_settings", list_settings))

    # Command to show help
    application.add_handler(CommandHandler("help", show_help))

    # Command to initiate image generation
    application.add_handler(CommandHandler("image", image_generation))

    # Handler for style selection
    application.add_handler(CallbackQueryHandler(style_selection_callback, pattern='|'.join(style.name for style in StylePreset)))


    # Handler for prompt input
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, prompt_handler))

    # Start the bot
    application.run_polling()
