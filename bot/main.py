import nest_asyncio
import logging

from telegram import Chat
from telegram.ext import ApplicationBuilder

from bot.config import get_telegram_token
from bot.dispatcher import command_handlers, callback_query_handlers, message_handlers
from bot.handlers.error_handler import error_handler
from scripts.utils.app_logger import setup_logging


logger = logging.getLogger(__name__)


if not hasattr(Chat, "FORUM"):
    Chat.FORUM = "forum"


def main() -> None:
    setup_logging()
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
