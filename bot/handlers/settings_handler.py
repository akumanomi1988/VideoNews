"""Read-only Telegram settings commands.

Config editing over chat was removed because it exposed credentials and allowed
unverified users to modify production configuration. Edit local settings.json
or environment variables, then restart the process.
"""

from telegram import Update
from telegram.ext import CallbackContext
from bot.services.settings_service import SettingsService


async def configure_setting(update: Update, context: CallbackContext) -> None:
    await update.effective_message.reply_text(
        "Settings are read-only in Telegram. Configure settings.json or environment "
        "variables on the server and restart VideoNews. Secrets are never shown in chat."
    )


async def list_settings(update: Update, context: CallbackContext) -> None:
    settings = SettingsService.load_settings()
    categories = sorted(str(key) for key in settings)
    summary = ", ".join(categories) if categories else "none (using runtime defaults/environment)"
    await update.effective_message.reply_text(
        f"Configured sections: {summary}. Values and credentials are hidden. "
        "Use /settings for configuration instructions."
    )


async def settings_category_selection_handler(update: Update, context: CallbackContext) -> None:
    await configure_setting(update, context)


async def setting_selection_handler(update: Update, context: CallbackContext) -> None:
    await configure_setting(update, context)


async def handle_new_value(update: Update, context: CallbackContext) -> None:
    await configure_setting(update, context)
