"""Fail-closed Telegram access control for all update types."""

import logging
import os
from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

logger = logging.getLogger(__name__)


def admin_user_ids(raw: str | None = None) -> frozenset[int]:
    """Allow only explicit numeric Telegram user IDs (never usernames)."""
    if raw is None:
        raw = os.getenv("TELEGRAM_ADMIN_USER_IDS") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    values = [x.strip() for x in raw.split(",") if x.strip()]
    try:
        ids = frozenset(int(x) for x in values)
    except ValueError as exc:
        raise ValueError("TELEGRAM_ADMIN_USER_IDS must contain numeric user IDs") from exc
    if any(i <= 0 for i in ids):
        raise ValueError("Telegram admin user IDs must be positive")
    return ids


def is_authorized(update: Update, authorized_ids: frozenset[int]) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    return bool(
        authorized_ids
        and user is not None
        and chat is not None
        and chat.type == "private"
        and user.id in authorized_ids
        and chat.id == user.id
    )


async def enforce_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registered in group -1 to reject all unauthorized updates before handlers."""
    if is_authorized(update, admin_user_ids()):
        return
    logger.warning("Rejected unauthorized Telegram update")
    if update.callback_query:
        await update.callback_query.answer("Not authorized", show_alert=True)
    elif update.effective_message and update.effective_chat and update.effective_chat.type == "private":
        await update.effective_message.reply_text("Not authorized.")
    raise ApplicationHandlerStop
