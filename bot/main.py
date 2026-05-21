import nest_asyncio
import logging

from telegram.ext import (
    ApplicationBuilder,
    # CommandHandler, # No longer directly used for registration here
    # CallbackQueryHandler, # No longer directly used for registration here
    # MessageHandler, # No longer directly used for registration here
    # filters, # No longer directly used for registration here
)

from bot.config import get_telegram_token
from bot.dispatcher import command_handlers, callback_query_handlers, message_handlers
from bot.handlers.error_handler import error_handler


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
        handlers=[logging.StreamHandler()]
    )
    # Optional: Set a higher log level for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)

    nest_asyncio.apply()

    telegram_token = get_telegram_token()
    if not telegram_token:
        logger.error("Error: TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    application = ApplicationBuilder().token(telegram_token).build()

    for handler in command_handlers:
        application.add_handler(handler)

    for handler in callback_query_handlers:
        application.add_handler(handler)

    for handler in message_handlers:
        application.add_handler(handler)

    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling()
    logger.info("Bot has stopped.")

if __name__ == '__main__':
    main()
