"""Centralized dispatcher for Telegram bot handlers."""

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.handlers import news_handler, settings_handler, utility_handler

command_handlers = [
    CommandHandler("help", utility_handler.help_command_handler),
    CommandHandler("settings", settings_handler.configure_setting),
    CommandHandler("show_settings", settings_handler.list_settings),
    CommandHandler("news_category", news_handler.show_category_selection),
    CommandHandler("topic_shortnews", news_handler.short_news_topic),
    CommandHandler("detailed_news", news_handler.long_news),
    CommandHandler("topic_longnews", news_handler.long_news_topic),
    CommandHandler("headless", news_handler.headless),
]

callback_query_handlers = [
    CallbackQueryHandler(
        settings_handler.settings_category_selection_handler,
        pattern=r"^([a-zA-Z_]+|cancel_config)$",
    ),
    CallbackQueryHandler(
        settings_handler.setting_selection_handler,
        pattern=r"^.+:.+$",
    ),
    CallbackQueryHandler(
        news_handler.news_category_selection_handler,
        pattern=r"^(business|entertainment|general|health|science|sports|technology|cancel_news_category)$",
    ),
    CallbackQueryHandler(
        news_handler.news_selection_handler,
        pattern=r"^(news_[0-9]+|cancel_news_selection)$",
    ),
]

message_handlers = [
    MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        settings_handler.handle_new_value,
    ),
    MessageHandler(filters.COMMAND, utility_handler.unknown_command_handler),
]
