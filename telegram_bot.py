# telegram_bot.py (main entry point after refactoring)

import asyncio
# import json # No longer needed for config here
# import os # No longer needed for config here
# import time # No longer needed here
import nest_asyncio # Keep for initial setup if not handled in bot.main
import logging 
import uuid # For generating unique error IDs
from telegram import Update 
from telegram.ext import CallbackContext 
from telegram.error import BadRequest, Forbidden # Specific error types

# Import the main function from bot.main
from bot.main import main as bot_main_runner
from bot.utils.message_sender import MessageSender 

# Create a logger instance for this module
logger = logging.getLogger(__name__)

async def error_handler(update: Update | None, context: CallbackContext) -> None:
    """Log Errors caused by Updates and inform the user if possible."""
    error_id = uuid.uuid4()
    base_log_message = f"Error ID: {error_id} - Exception while handling an update"
    
    # Log the full error with stack trace first
    logger.error(f"{base_log_message}: {context.error}", exc_info=context.error)

    message_sender = MessageSender(context=context)
    user_message = f"An unexpected error occurred. Please try again later. If the problem persists, please report this error ID: {error_id}"

    if isinstance(context.error, BadRequest):
        logger.warning(f"Error ID: {error_id} - BadRequest: {context.error}. This might be due to a malformed request or message content.")
        # More specific messages could be crafted based on context.error.message
        if "message is too long" in str(context.error).lower():
            user_message = f"The message or content is too long. Please try with a shorter version. (Error ID: {error_id})"
        elif "wrong file identifier" in str(context.error).lower() or "wrong type of the web page content" in str(context.error).lower():
             user_message = f"There was an issue with the media or link provided. Please check and try again. (Error ID: {error_id})"
        else:
            user_message = f"There was an issue with your request (e.g., invalid characters or format). Please check and try again. (Error ID: {error_id})"
    
    elif isinstance(context.error, Forbidden):
        logger.warning(f"Error ID: {error_id} - Forbidden: {context.error}. Bot might be blocked by the user or kicked from the group.")
        # No message can be sent if the bot is blocked or not in the chat.
        # We can log this, but sending a message will likely fail.
        # If update and update.effective_chat exist, we can try, but expect it to fail.
        if update and update.effective_chat:
            logger.info(f"Error ID: {error_id} - Attempting to notify user about Forbidden error in chat {update.effective_chat.id}, but it will likely fail.")
        # No user_message is set here as it would likely fail.
        return # Exit early as we probably can't send a message

    elif "[WinError 32]" in str(context.error): # Keep existing WinError 32 handling
        logger.warning(f"Error ID: {error_id} - Detected file access error [WinError 32].")
        if update: 
            try:
                await message_sender.send_message(
                    update=update, 
                    text=f"A temporary system file issue occurred. Please wait a moment, it might be retried. (Error ID: {error_id})"
                )
            except Exception as e_reply:
                logger.error(f"Error ID: {error_id} - Failed to send WinError 32 retry message to user: {e_reply}", exc_info=True)
        await asyncio.sleep(5) 
        return

    # Send the determined user_message
    if update: 
        try:
            await message_sender.send_message(update=update, text=user_message)
        except Exception as e_reply:
            logger.error(f"Error ID: {error_id} - Failed to send error message to user: {e_reply}", exc_info=True)

# All other functions (configure_setting, category_selection_handler, etc.) have been moved.
# The main part of the bot (ApplicationBuilder, handler registration, run_polling)
# is now in bot/main.py.

if __name__ == '__main__':
    # Basic logging configuration for standalone execution of this file (though it mostly calls bot.main)
    # This ensures that if this file is run directly for some reason, logs are configured.
    # However, bot.main.py should be the primary entry point and configure logging there.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    logger.info("Starting bot from telegram_bot.py...")
    # Call the main runner function from bot.main
    # bot.main.main() is expected to configure its own logging as the primary entry point.
    bot_main_runner()
    logger.info("Bot process ended.")