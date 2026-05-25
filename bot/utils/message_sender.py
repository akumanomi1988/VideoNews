"""
Utility for sending Telegram messages with retry logic.

This module provides the `MessageSender` class, which abstracts the details
of sending messages through the Telegram Bot API. It intelligently chooses
the correct method to reply to an update (e.g., from a message or a callback query)
or send a new message to a specified chat ID.

Key features include:
- Automatic retry mechanism for transient Telegram API errors (e.g., timeouts,
  network issues) for all sending operations.
- Support for sending messages to regular chats and topics within forum-enabled groups.
- Graceful handling of different update types (message vs. callback query).
"""
import logging
from typing import Callable, Any, Awaitable, Optional # For type hinting
from telegram import Update, InlineKeyboardMarkup, Chat, Message as TelegramMessage # Renamed Message
from telegram.ext import CallbackContext
from bot.utils.retry_utils import retry_on_telegram_error
from scripts.utils.app_logger import trace

# Create a logger instance for this module
logger = logging.getLogger(__name__)

class MessageSender:
    """
    A class to handle sending messages with integrated retry logic.

    This class determines the appropriate Telegram API method to use based on
    the provided `Update` object or `chat_id`. It uses a retry decorator
    for underlying send operations to handle transient network issues.

    Attributes:
        context (Optional[CallbackContext]): The CallbackContext, which can provide
                                             `context.bot` for sending messages.
    """

    @trace()
    def __init__(self, context: Optional[CallbackContext] = None) -> None:
        """
        Initializes the MessageSender.

        Args:
            context: Optional. The CallbackContext associated with the current
                     update handling, useful for accessing `context.bot`.
        """
        self.context: Optional[CallbackContext] = context
        logger.debug("MessageSender initialized.")

    @trace()
    @retry_on_telegram_error(max_retries=3, delay_seconds=2)
    async def _send_with_retry(self, 
                               message_callable: Callable[..., Awaitable[TelegramMessage]], 
                               *args: Any, 
                               **kwargs: Any
                              ) -> TelegramMessage:
        """
        Internal method that calls the provided Telegram message sending function 
        with retry logic.

        Args:
            message_callable: The specific Telegram send method to call (e.g., `update.message.reply_text`).
            *args: Positional arguments for `message_callable`.
            **kwargs: Keyword arguments for `message_callable`.

        Returns:
            The result of the `message_callable` (typically a `telegram.Message` object).
        
        Raises:
            TelegramError: If all retries fail for a Telegram-specific error.
            Exception: For non-Telegram errors or if retries fail without a specific Telegram error.
        """
        logger.debug(f"Attempting to send message via {message_callable.__name__} with args: {args}, kwargs: {kwargs}")
        return await message_callable(*args, **kwargs)

    @trace()
    async def send_message(
        self, 
        update: Optional[Update] = None, 
        text: str = "", 
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        chat_id: Optional[int | str] = None,
        message_thread_id: Optional[int] = None
    ) -> None:
        """
        Sends a message using the most appropriate method based on the provided
        `update` or `chat_id`. It automatically handles retries.

        The method prioritizes sending as a reply if `update` is provided.
        If `chat_id` is given, it overrides `update` for targeting the message.
        If `message_thread_id` is provided, it's used for sending to topics in forums.

        Args:
            update: Optional. The `telegram.Update` object from which to derive
                    the chat ID and potentially reply to.
            text: The text of the message. Defaults to an empty string. If empty
                  and no `reply_markup` is provided, a placeholder text is sent.
            reply_markup: Optional. An `InlineKeyboardMarkup` for the message.
            chat_id: Optional. The target chat ID. If provided, this overrides
                     the chat ID from `update`.
            message_thread_id: Optional. Unique identifier for the target message
                               thread (topic) of the forum. If the `update` object
                               indicates a topic message, this ID might be
                               auto-populated if not explicitly provided.
        """
        effective_chat_id: Optional[int | str] = None
        target_description: str = "N/A"
        effective_message_thread_id: Optional[int] = message_thread_id # Prioritize explicitly passed

        if update and update.effective_chat:
            effective_chat_id = update.effective_chat.id
            target_description = f"chat_id {effective_chat_id} from update.effective_chat"
            # Auto-populate message_thread_id if it's a topic message and not already set
            if not effective_message_thread_id and update.effective_message and \
               update.effective_message.is_topic_message and update.effective_message.message_thread_id:
                effective_message_thread_id = update.effective_message.message_thread_id
            
            if effective_message_thread_id:
                 target_description += f", message_thread_id {effective_message_thread_id}"

        if chat_id: # Explicit chat_id overrides update's chat_id for targeting
            effective_chat_id = chat_id
            target_description = f"explicit chat_id {chat_id}"
            if effective_message_thread_id: # Already set or passed explicitly
                 target_description += f", message_thread_id {effective_message_thread_id}"

        current_text: str = text
        if not current_text and not reply_markup: 
            logger.warning("send_message called with empty text and no reply_markup. Sending a placeholder.")
            current_text = "(empty message)"


        try:
            if update and update.callback_query and update.callback_query.message:
                logger.info(f"Sending message via callback_query.message.reply_text to {target_description}")
                # Determine if the original callback message was in a topic
                is_topic_context = (update.callback_query.message.is_topic_message or 
                                    (update.effective_chat and update.effective_chat.type == 'forum'))
                await self._send_with_retry(
                    update.callback_query.message.reply_text, 
                    text=current_text, 
                    reply_markup=reply_markup,
                    message_thread_id=effective_message_thread_id if is_topic_context else None
                )
            elif update and update.message:
                logger.info(f"Sending message via update.message.reply_text to {target_description}")
                is_topic_context = (update.message.is_topic_message or
                                    (update.effective_chat and update.effective_chat.type == 'forum'))
                await self._send_with_retry(
                    update.message.reply_text, 
                    text=current_text, 
                    reply_markup=reply_markup,
                    message_thread_id=effective_message_thread_id if is_topic_context else None
                )
            elif effective_chat_id and self.context and self.context.bot:
                logger.info(f"Sending message via context.bot.send_message to {target_description}")
                await self._send_with_retry(
                    self.context.bot.send_message, 
                    chat_id=effective_chat_id, 
                    text=current_text, 
                    reply_markup=reply_markup,
                    message_thread_id=effective_message_thread_id
                )
            elif effective_chat_id: 
                logger.warning(f"Sending message to chat_id {effective_chat_id} but no CallbackContext (or bot instance) provided to MessageSender. This will likely fail.")
                raise ValueError("Cannot send message: bot instance not available. Provide CallbackContext to MessageSender.")
            else:
                logger.error("send_message called without a valid update object or explicit chat_id. No message sent.")
        except Exception as e:
            logger.error(f"Failed to send message to {target_description}: {e}", exc_info=True)
            # Depending on desired behavior, could re-raise or just log.
            # If re-raised, the caller needs to handle it.
            # raise

if __name__ == '__main__':
    # This is a conceptual test and requires a running bot environment or mocks.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("MessageSender self-test section (conceptual).")

    # Mock Update and Context for local testing (very basic)
    class MockBot:
        async def send_message(self, chat_id, text, reply_markup=None, message_thread_id=None):
            logger.info(f"MockBot.send_message: chat_id={chat_id}, text='{text}', reply_markup={reply_markup is not None}, message_thread_id={message_thread_id}")
            # Simulate a Telegram API error for retry testing
            if not hasattr(self, 'attempts'):
                self.attempts = 0
            self.attempts += 1
            if self.attempts <= 2 and text == "Test with retry": # Fail first 2 attempts for a specific message
                logger.warning(f"MockBot: Simulating NetworkError on attempt {self.attempts}")
                raise NetworkError("Simulated network error from MockBot")
            return f"Message '{text}' sent to {chat_id}."

    class MockMessage:
        def __init__(self, chat_id, message_id=123, is_topic_message=False, message_thread_id=None):
            self.chat_id = chat_id
            self.message_id = message_id
            self.is_topic_message = is_topic_message
            self.message_thread_id = message_thread_id
        
        async def reply_text(self, text, reply_markup=None, message_thread_id=None):
            # This mock needs to access MockBot or have its own send_message logic
            logger.info(f"MockMessage.reply_text: chat_id={self.chat_id}, text='{text}', reply_markup={reply_markup is not None}, message_thread_id={message_thread_id}")
            # Simulate a Telegram API error for retry testing
            if not hasattr(self, 'reply_attempts'):
                self.reply_attempts = 0
            self.reply_attempts += 1
            if self.reply_attempts <= 2 and "retry" in text.lower(): # Fail first 2 attempts for messages containing "retry"
                logger.warning(f"MockMessage: Simulating TimedOut on attempt {self.reply_attempts}")
                raise TimedOut("Simulated timeout from MockMessage.reply_text")
            return f"Message '{text}' replied to in chat {self.chat_id}."

    class MockCallbackQuery:
        def __init__(self, message):
            self.message = message
    
    class MockUpdate:
        def __init__(self, message=None, callback_query=None, effective_chat_id=None):
            self.message = message
            self.callback_query = callback_query
            self._effective_chat_id = effective_chat_id

        @property
        def effective_chat(self):
            if self._effective_chat_id:
                return Chat(id=self._effective_chat_id, type="private") # Basic mock
            if self.message:
                return Chat(id=self.message.chat_id, type="private")
            if self.callback_query and self.callback_query.message:
                return Chat(id=self.callback_query.message.chat_id, type="private")
            return None
        
        @property
        def effective_message(self): # Added for message_thread_id logic
            if self.callback_query:
                return self.callback_query.message
            return self.message


    async def test_message_sender():
        logger.info("--- Testing MessageSender ---")
        mock_bot_instance = MockBot()
        mock_context = CallbackContext(bot=mock_bot_instance, dispatcher=None) # Basic mock
        
        sender_with_context = MessageSender(context=mock_context)
        sender_no_context = MessageSender()

        # Test 1: Using update.message
        logger.info("\nTest 1: update.message")
        msg1 = MockMessage(chat_id=1001)
        upd1 = MockUpdate(message=msg1)
        await sender_no_context.send_message(update=upd1, text="Hello from update.message")
        
        logger.info("\nTest 1.1: update.message with retry")
        msg1_retry = MockMessage(chat_id=1002)
        upd1_retry = MockUpdate(message=msg1_retry)
        await sender_no_context.send_message(update=upd1_retry, text="Test with retry (update.message)")

        # Test 2: Using update.callback_query
        logger.info("\nTest 2: update.callback_query")
        cb_msg = MockMessage(chat_id=2001)
        cb_query = MockCallbackQuery(message=cb_msg)
        upd2 = MockUpdate(callback_query=cb_query)
        await sender_no_context.send_message(update=upd2, text="Hello from callback_query")

        # Test 3: Using context.bot.send_message (chat_id provided)
        logger.info("\nTest 3: context.bot.send_message (via chat_id)")
        await sender_with_context.send_message(chat_id=3001, text="Hello from context.bot")

        logger.info("\nTest 3.1: context.bot.send_message with retry")
        # Reset attempts for this specific path if MockBot state is shared
        mock_bot_instance.attempts = 0 
        await sender_with_context.send_message(chat_id=3002, text="Test with retry")


        # Test 4: No valid update or chat_id (should log error)
        logger.info("\nTest 4: No valid update or chat_id")
        await sender_no_context.send_message(text="This should not send")
        
        # Test 5: update.message with topic
        logger.info("\nTest 5: update.message with topic_message_id")
        topic_msg = MockMessage(chat_id=-1001987654321, message_id=789, is_topic_message=True, message_thread_id=12)
        upd_topic = MockUpdate(message=topic_msg, effective_chat_id=-1001987654321)
        await sender_no_context.send_message(update=upd_topic, text="Hello to topic from update.message")
        
        # Test 6: Explicit chat_id and message_thread_id with context
        logger.info("\nTest 6: Explicit chat_id and message_thread_id with context")
        await sender_with_context.send_message(chat_id=-1001987654321, text="Hello to topic via explicit chat_id and message_thread_id", message_thread_id=15)


    import asyncio
    # asyncio.run(test_message_sender()) # Requires careful mocking or actual bot for full test.
    logger.info("Conceptual tests for MessageSender defined. Run with a proper asyncio setup and mocks if needed.")
