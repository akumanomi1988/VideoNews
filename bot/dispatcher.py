"""Single Telegram dispatcher: authorization and stateful message routing."""
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.auth import protected
from bot.handlers import news_handler, settings_handler, utility_handler


async def handle_private_text(update, context):
    """Avoid competing catch-all message handlers: only the active flow consumes text."""
    state = context.user_data
    if state.get("awaiting_article_text"):
        await news_handler.handle_article_text(update, context)
    elif state.get("category") and state.get("setting"):
        await settings_handler.handle_new_value(update, context)


commands = {
    "start": utility_handler.help_command_handler,
    "help": utility_handler.help_command_handler,
    "settings": settings_handler.configure_setting,
    "show_settings": settings_handler.list_settings,
    "news_category": news_handler.show_category_selection,
    "topic_shortnews": news_handler.short_news_topic,
    "topic_longnews": news_handler.long_news_topic,
    "detailed_news": news_handler.long_news,
    "headless": news_handler.headless,
    "url_shortnews": news_handler.url_short_news,
    "url_longnews": news_handler.url_long_news,
    "text_shortnews": news_handler.text_shortnews,
    "text_longnews": news_handler.text_longnews,
}
command_handlers = [CommandHandler(name, protected(handler)) for name, handler in commands.items()]

callback_query_handlers = [
    CallbackQueryHandler(protected(news_handler.news_category_selection_handler),
        pattern=r"^(business|entertainment|general|health|science|sports|technology|cancel_news_category)$"),
    CallbackQueryHandler(protected(news_handler.news_selection_handler),
        pattern=r"^(news_[0-9]+|cancel_news_selection)$"),
    CallbackQueryHandler(protected(news_handler.style_selection_handler),
        pattern=r"^(style_[A-Z_]+|cancel_style)$"),
    CallbackQueryHandler(protected(settings_handler.settings_category_selection_handler),
        pattern=r"^([a-zA-Z_]+|cancel_config)$"),
    CallbackQueryHandler(protected(settings_handler.setting_selection_handler), pattern=r"^.+:.+$"),
]

message_handlers = [
    MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, protected(handle_private_text)),
    MessageHandler(filters.COMMAND, protected(utility_handler.unknown_command_handler)),
]
