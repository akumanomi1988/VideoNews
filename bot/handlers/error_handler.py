"""Global Telegram error handler."""

import asyncio
import logging
import uuid
from typing import Optional

from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import CallbackContext

from bot.utils.message_sender import MessageSender

logger = logging.getLogger(__name__)


async def error_handler(update: Optional[Update], context: CallbackContext) -> None:
    """Log errors and notify the user when possible."""
    error_id = uuid.uuid4()
    base_log_message = f"Error ID: {error_id} - Exception while handling an update"

    logger.error(f"{base_log_message}: {context.error}", exc_info=context.error)

    message_sender = MessageSender(context=context)
    user_message = (
        "An unexpected error occurred. Please try again later. "
        f"If the problem persists, please report this error ID: {error_id}"
    )

    if isinstance(context.error, BadRequest):
        logger.warning(
            f"Error ID: {error_id} - BadRequest: {context.error}."
        )
        error_text = str(context.error).lower()
        if "message is too long" in error_text:
            user_message = f"The message or content is too long. Please try with a shorter version. (Error ID: {error_id})"
        elif "wrong file identifier" in error_text or "wrong type of the web page content" in error_text:
            user_message = f"There was an issue with the media or link provided. Please check and try again. (Error ID: {error_id})"
        else:
            user_message = f"There was an issue with your request. Please check and try again. (Error ID: {error_id})"
    elif isinstance(context.error, Forbidden):
        logger.warning(f"Error ID: {error_id} - Forbidden: {context.error}.")
        return
    elif "[WinError 32]" in str(context.error):
        logger.warning(f"Error ID: {error_id} - Detected file access error [WinError 32].")
        if update:
            try:
                await message_sender.send_message(
                    update=update,
                    text=f"A temporary system file issue occurred. Please wait a moment. (Error ID: {error_id})"
                )
            except Exception as e_reply:
                logger.error(
                    f"Error ID: {error_id} - Failed to send WinError 32 retry message: {e_reply}",
                    exc_info=True,
                )
        await asyncio.sleep(5)
        return

    if update:
        try:
            await message_sender.send_message(update=update, text=user_message)
        except Exception as e_reply:
            logger.error(
                f"Error ID: {error_id} - Failed to send error message to user: {e_reply}",
                exc_info=True,
            )
