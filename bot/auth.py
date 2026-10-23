"""Fail-closed authorization for every Telegram entry point."""
from __future__ import annotations

import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)


def allowed_user_ids() -> frozenset[int]:
    raw = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")
    try:
        return frozenset(int(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError:
        logger.error("Invalid TELEGRAM_ALLOWED_USER_IDS; deny all until corrected")
        return frozenset()


def is_authorized(user_id: int | None) -> bool:
    return user_id is not None and user_id in allowed_user_ids()


def protected(handler):
    """Wrap commands, callbacks and private messages without changing their API."""
    @wraps(handler)
    async def wrapper(update, context):
        user = getattr(update, "effective_user", None)
        user_id = getattr(user, "id", None)
        if not is_authorized(user_id):
            logger.warning("Denied Telegram request from user %s", user_id)
            query = getattr(update, "callback_query", None)
            if query:
                await query.answer("Not authorized", show_alert=True)
            else:
                message = getattr(update, "effective_message", None)
                if message:
                    await message.reply_text("Not authorized.")
            return
        return await handler(update, context)
    return wrapper
