"""Telegram router. All updates are authorized by bot.main's group -1 gate."""

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters
from bot.handlers import news_handler, settings_handler, utility_handler

command_handlers = [
    CommandHandler("start", utility_handler.help_command_handler),
    CommandHandler("help", utility_handler.help_command_handler),
    CommandHandler("settings", settings_handler.configure_setting),
    CommandHandler("show_settings", settings_handler.list_settings),
    CommandHandler("news_category", news_handler.show_category_selection),
    CommandHandler("topic_shortnews", news_handler.short_news_topic),
    CommandHandler("topic_longnews", news_handler.long_news_topic),
    CommandHandler("detailed_news", news_handler.long_news),
    CommandHandler("headless", news_handler.headless),
    CommandHandler("url_shortnews", news_handler.url_short_news),
    CommandHandler("url_longnews", news_handler.url_long_news),
    CommandHandler("text_shortnews", news_handler.text_shortnews),
    CommandHandler("text_longnews", news_handler.text_longnews),
]

callback_query_handlers = [
    CallbackQueryHandler(news_handler.news_category_selection_handler,
                         pattern=r"^(business|entertainment|general|health|science|sports|technology|cancel_news_category)$"),
    CallbackQueryHandler(news_handler.news_selection_handler,
                         pattern=r"^(news_[0-9]+|cancel_news_selection)$"),
    CallbackQueryHandler(news_handler.style_selection_handler,
                         pattern=r"^(style_[A-Z_]+|cancel_style)$"),
]

# One handler for private text: the old first handler shadowed settings input.
# Settings mutation from Telegram is now disabled, so all free text is article input.
message_handlers = [
    MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
                   news_handler.handle_article_text),
    MessageHandler(filters.COMMAND, utility_handler.unknown_command_handler),
]
