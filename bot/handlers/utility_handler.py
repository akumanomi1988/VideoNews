"""
Utility command handlers for the Telegram bot.

This module contains handlers for common utility commands such as:
- /help: Displays a help message with available commands.
- Unknown command handler: Responds to commands not recognized by the bot.
"""
import logging
from typing import Optional # For type hinting User
from telegram import Update, User as TelegramUser # Renamed User to avoid conflict
from telegram.ext import CallbackContext
from bot.utils.message_sender import MessageSender
from scripts.utils.app_logger import trace

# Create a logger instance for this module
logger = logging.getLogger(__name__)

@trace()
async def unknown_command_handler(update: Update, context: CallbackContext) -> None:
    """
    Handles unrecognized commands sent to the bot.
    Logs the unknown command and informs the user.
    """
    message_sender = MessageSender(context=context)
    user: Optional[TelegramUser] = update.message.from_user if update.message else None
    user_id_log: str = str(user.id) if user else "UnknownUser"
    command_text: str = update.message.text if update.message else "N/A"
    
    logger.warning(f"Unknown command: '{command_text}' from user {user_id_log}")
    
    await message_sender.send_message(
        update=update,
        text="Sorry, I didn't understand that command. Try /help to see available commands. 🤔"
    )

@trace()
async def help_command_handler(update: Update, context: CallbackContext) -> None:
    """
    Handles the /help command.
    Sends a message listing available commands and their descriptions.
    """
    message_sender = MessageSender(context=context)
    user: Optional[TelegramUser] = update.message.from_user if update.message else None
    user_id_log: str = str(user.id) if user else "UnknownUser"
    logger.info(f"Help command used by user {user_id_log}")

    help_text: str = (
        "Comandos disponibles:\n\n"
        "[NOTICIAS]\n"
        "  /topic_shortnews <tema> - Video corto de noticias sobre un tema (FLUJO A)\n"
        "  /topic_longnews <tema> - Video largo de noticias sobre un tema\n"
        "  /url_shortnews <url> - Video corto desde enlace de noticia (FLUJO B)\n"
        "  /url_longnews <url> - Video largo desde enlace de noticia\n"
        "  /news_category - Elegir categoria y obtener noticias\n"
        "  /detailed_news - Noticia detallada por categoria (video largo)\n"
        "  /headless [num] - Procesar noticias virales (solo admins)\n\n"
        "[CONFIGURACION]\n"
        "  /settings - Configurar opciones del bot\n"
        "  /show_settings - Mostrar configuracion actual\n\n"
        "[UTILES]\n"
        "  /help - Mostrar esta ayuda\n"
    )
    
    await message_sender.send_message(
        update=update,
        text=help_text,
        # For MarkdownV2, use parse_mode='MarkdownV2'. Ensure special characters are escaped.
        # For plain text, remove parse_mode or use None.
        # Given the asterisks, Markdown would be nice. Let's assume MessageSender can handle it or we add it.
        # For now, sending as plain text to avoid unescaped character issues until MessageSender is enhanced.
    )

if __name__ == '__main__':
    # Conceptual test for help_command_handler
    logging.basicConfig(level=logging.INFO)
    
    class MockUser:
        def __init__(self, id):
            self.id = id

    class MockMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.from_user = MockUser(user_id)

    class MockUpdate:
        def __init__(self, message_text, user_id=123):
            self.message = MockMessage(message_text, user_id)
            self.effective_chat = None # MessageSender might need this for some paths

    class MockContext:
        def __init__(self):
            self.bot = None # MessageSender might need this

    import asyncio
    async def test_handlers():
        mock_update_help = MockUpdate("/help")
        mock_context_help = MockContext()
        logger.info("Testing help_command_handler:")
        await help_command_handler(mock_update_help, mock_context_help)
        
        mock_update_unknown = MockUpdate("/randomcommand")
        mock_context_unknown = MockContext()
        logger.info("\nTesting unknown_command_handler:")
        await unknown_command_handler(mock_update_unknown, mock_context_unknown)

    # asyncio.run(test_handlers()) # Requires MessageSender's mock to not fail on send
    logger.info("Conceptual tests for utility_handler.py defined.")
