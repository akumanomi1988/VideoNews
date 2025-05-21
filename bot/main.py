import asyncio # For nest_asyncio if used here, or general async operations
import nest_asyncio
import logging # Added for logging
import sys # Added for StreamHandler, though logging.StreamHandler() works directly

from telegram.ext import (
    ApplicationBuilder,
    # CommandHandler, # No longer directly used for registration here
    # CallbackQueryHandler, # No longer directly used for registration here
    # MessageHandler, # No longer directly used for registration here
    # filters, # No longer directly used for registration here
)

from bot.config import get_telegram_token
# Remove direct handler imports
# from bot.handlers.settings_handler import (
#     configure_setting,
#     settings_category_selection_handler, # Renamed in settings_handler.py
#     setting_selection_handler,
#     handle_new_value,
#     list_settings,
# )
# from bot.handlers.news_handler import (
#     show_category_selection as news_show_category_selection, # Alias to avoid name clash
#     news_category_selection_handler, # Renamed in news_handler.py
#     news_selection_handler,
#     short_news_topic,
#     long_news_topic,
#     long_news,
#     headless,
# )
from bot.dispatcher import command_handlers, callback_query_handlers, message_handlers

# Attempt to import error_handler from telegram_bot.py
# This creates a temporary circular dependency if telegram_bot.py also tries to import from bot.main
# A better solution would be to move error_handler to its own file e.g. bot/handlers/error_handler.py
# For now, let's define a placeholder error_handler here if direct import is problematic,
# or assume it will be moved. The subtask mentioned keeping it in telegram_bot.py for now.
# So, this import will be problematic until telegram_bot.py is refactored.
# Import error_handler from telegram_bot.py
# This assumes telegram_bot.py is in the python path and structured to allow this import.
# Given telegram_bot.py is at the root and bot/ is a subdirectory, this might need path adjustments
# or a restructuring of where error_handler is defined if direct import fails.
# For now, proceeding with the assumption it's resolvable.
# If this causes issues, error_handler should be moved to a neutral location e.g. bot/handlers/error.py
from telegram_bot import error_handler


# Create a logger instance for this module
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Initializes and runs the Telegram bot application.

    This function performs the following steps:
    1. Configures basic logging for the application.
    2. Applies `nest_asyncio` to allow asyncio event loops to be nested,
       which is useful in environments like Jupyter notebooks or when an
       event loop is already running.
    3. Retrieves the Telegram bot token using `get_telegram_token()`.
       If the token is not found, it logs an error and exits.
    4. Builds the `telegram.ext.Application` using the token.
    5. Registers command, callback query, and message handlers loaded from
       `bot.dispatcher`.
    6. Registers the global error handler (`telegram_bot.error_handler`).
    7. Starts the bot by polling for updates.
    8. Logs when the bot has stopped.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()] # Explicitly use sys.stdout if needed, but StreamHandler defaults to stderr
    )
    # Optional: Set a higher log level for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING) # Corrected from telegram.ext to a valid logger name if needed, or specific submodules

    nest_asyncio.apply() # Apply nest_asyncio

    telegram_token = get_telegram_token()
    if not telegram_token:
        logger.error("Error: TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    application = ApplicationBuilder().token(telegram_token).build()

    # Register command handlers
    for handler in command_handlers:
        application.add_handler(handler)

    # Register callback query handlers
    for handler in callback_query_handlers:
        application.add_handler(handler)

    # Register message handlers
    for handler in message_handlers:
        application.add_handler(handler)

    # Register the error handler (kept separate)
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Bot is starting...")
    application.run_polling()
    logger.info("Bot has stopped.")

if __name__ == '__main__':
    main()
