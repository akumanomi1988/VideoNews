"""
Settings-related command and callback query handlers for the Telegram bot.

This module provides handlers for configuring bot settings.
These handlers interact with the `SettingsService` to load and save settings,
which currently uses a JSON file (`settings.json`). This is considered an
older system and may be phased out or refactored in the future.

Commands:
- /settings: Initiates the process to configure settings.
- /show_settings: Displays the current settings.

Callback Query Handling:
- Handles selection of a setting category.
- Handles selection of a specific setting within a category.

Message Handling:
- Handles the new value provided by the user for a selected setting.
"""
import logging 
from typing import Dict, Any, Optional, List # For type hinting
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import CallbackContext
from bot.services.settings_service import SettingsService
from bot.utils.message_sender import MessageSender # Added MessageSender
from scripts.utils.app_logger import trace

# Create a logger instance for this module
logger = logging.getLogger(__name__)

@trace()
async def configure_setting(update: Update, context: CallbackContext) -> None:
    """
    Initiates the process for configuring settings (old JSON-based system).
    Displays a list of setting categories for the user to choose from.
    Triggered by the /settings command.
    """
    logger.info("configure_setting called. This function uses the old settings system.")
    message_sender = MessageSender(context=context)
    settings: Dict[str, Any] = SettingsService.load_settings() 
    categories: List[str] = list(settings.keys())
    
    valid_categories: List[str] = [cat for cat in categories if isinstance(cat, str)]
    keyboard_buttons: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(category.capitalize(), callback_data=category)]
        for category in valid_categories
    ]
    keyboard_buttons.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_config')])
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    
    await message_sender.send_message(
        update=update,
        text="Please select a setting category to modify or cancel:",
        reply_markup=reply_markup
    )

@trace()
async def settings_category_selection_handler(update: Update, context: CallbackContext) -> None:
    """
    Handles the user's selection of a settings category.
    Displays the settings within the selected category and options to modify them.
    This interacts with the old JSON-based settings system.
    """
    query: Optional[CallbackQuery] = update.callback_query
    if not query or not query.data:
        logger.warning("settings_category_selection_handler called without query or query.data")
        return

    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Could not answer callback query (may be expired): {e}")

    message_sender = MessageSender(context=context)

    if query.data == 'cancel_config':
        logger.info("Configuration selection cancelled by user.")
        await message_sender.send_message(update=update, text="Configuration selection cancelled. ✅")
        return
        
    selected_category: str = query.data
    logger.info(f"User selected settings category: {selected_category}. This function uses the old settings system.")
    settings: Dict[str, Any] = SettingsService.load_settings()
    category_settings: Dict[str, Any] = settings.get(selected_category, {})
    
    valid_keys: List[str] = [key for key in category_settings.keys() if isinstance(key, str)]
    response_text: str = f"Configuration for *{selected_category.capitalize()}*:\n"
    for key in valid_keys:
        response_text += f"- {key}\n"
    response_text += "\nSelect a setting to modify or cancel."
    
    keyboard_buttons_settings: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(key, callback_data=f"{selected_category}:{key}")] 
        for key in valid_keys
    ]
    keyboard_buttons_settings.append([InlineKeyboardButton("Cancel 🛑", callback_data='cancel_config')])
    reply_markup_settings = InlineKeyboardMarkup(keyboard_buttons_settings)
    
    await message_sender.send_message(update=update, text=response_text, reply_markup=reply_markup_settings)

@trace()
async def setting_selection_handler(update: Update, context: CallbackContext) -> None:
    """
    Handles the user's selection of a specific setting to modify.
    Displays the current value and prompts the user for a new value.
    This interacts with the old JSON-based settings system.
    """
    query: Optional[CallbackQuery] = update.callback_query
    if not query or not query.data:
        logger.warning("setting_selection_handler called without query or query.data")
        return

    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Could not answer callback query (may be expired): {e}")

    message_sender = MessageSender(context=context)

    if query.data == 'cancel_config':
        logger.info("Setting selection cancelled by user.")
        await message_sender.send_message(update=update, text="Configuration selection cancelled. ✅")
        return
        
    try:
        selected_category, selected_setting = query.data.split(':', 1)
    except ValueError:
        logger.error(f"Invalid callback data format in setting_selection_handler: {query.data}", exc_info=True)
        await message_sender.send_message(update=update, text="An internal error occurred. Please try again. 🛠️")
        return

    logger.info(f"User selected setting: {selected_category}:{selected_setting} for modification.")
    settings: Dict[str, Any] = SettingsService.load_settings()
    current_value: str = "NOT_AVAILABLE (old system)" 
    category_data: Optional[Dict[str, Any]] = settings.get(selected_category)
    if category_data and isinstance(category_data, dict):
        current_value = str(category_data.get(selected_setting, "NOT_AVAILABLE (key not found)"))

    await message_sender.send_message(
        update=update, 
        text=f"Current value for *{selected_setting}* is `{current_value}`.\nPlease enter a new value:"
    )
    context.user_data['category'] = selected_category # type: ignore[attr-defined]
    context.user_data['setting'] = selected_setting # type: ignore[attr-defined]

@trace()
async def handle_new_value(update: Update, context: CallbackContext) -> None:
    """
    Handles the text message containing the new value for a setting.
    Updates the setting in the JSON file via SettingsService.
    This interacts with the old JSON-based settings system.
    """
    message_sender = MessageSender(context=context)
    user_data: Optional[Dict[str, Any]] = context.user_data # type: ignore[attr-defined]

    if user_data and 'category' in user_data and 'setting' in user_data:
        selected_category_from_context: str = user_data['category']
        selected_setting_from_context: str = user_data['setting']
        new_value: str = update.message.text if update.message and update.message.text else ""
        
        logger.info(f"Attempting to update setting '{selected_category_from_context}:{selected_setting_from_context}' to '{new_value}'.")
        
        try:
            settings: Dict[str, Any] = SettingsService.load_settings()
            if selected_category_from_context not in settings:
                logger.info(f"Creating new category '{selected_category_from_context}' in settings.")
                settings[selected_category_from_context] = {}
            
            settings[selected_category_from_context][selected_setting_from_context] = new_value
            SettingsService.save_settings(settings)
            
            logger.info(f"Successfully updated setting '{selected_category_from_context}:{selected_setting_from_context}' to '{new_value}'.")
            await message_sender.send_message(
                update=update, 
                text=f"The setting *{selected_setting_from_context}* in category *{selected_category_from_context}* has been updated to `{new_value}` ✅"
            )
        except Exception as e:
            logger.error(f"Error saving setting '{selected_category_from_context}:{selected_setting_from_context}': {e}", exc_info=True)
            await message_sender.send_message(update=update, text="An error occurred while saving the setting. Please try again. 🛠️")
        finally:
            user_data.clear()
    else:
        logger.warning("handle_new_value called but 'category' or 'setting' not in user_data.")
        # This message might be sent if a user sends random text after a command flow has expired or been cleared.
        # Consider if a response is always needed or if it should fail silently if not in a settings flow.
        # For now, keeping the response as it might indicate a broken conversation flow to the user.
        await message_sender.send_message(update=update, text="No setting selected for update. Please start by using the /settings command. ⚙️")

@trace()
async def list_settings(update: Update, context: CallbackContext) -> None:
    """
    Handles the /show_settings command.
    Displays all current settings from the JSON file.
    This interacts with the old JSON-based settings system.
    """
    logger.info("list_settings called.")
    message_sender = MessageSender(context=context)
    settings: Dict[str, Any] = SettingsService.load_settings()
    if not settings:
        logger.info("No settings found or settings file is empty.")
        await message_sender.send_message(update=update, text="No settings are currently configured or the settings file is empty. 🤷")
        return

    response_text: str = "Available settings (from JSON file):\n\n"
    for section, config_items in settings.items():
        response_text += f"*{section}*\n"
        if isinstance(config_items, dict):
            for key, value in config_items.items():
                response_text += f"  - {key}: `{value}`\n" 
        else:
            response_text += f"  - `{config_items}`\n" 
        response_text += "\n"
    
    if response_text == "Available settings (from JSON file):\n\n": 
        logger.warning("Settings object was not empty, but response string is still initial value.")
        await message_sender.send_message(update=update, text="Found settings, but could not format them. 🤔")
    else:
        await message_sender.send_message(update=update, text=response_text)
