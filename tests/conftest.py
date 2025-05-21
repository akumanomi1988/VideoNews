import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from telegram import Update as TelegramUpdate # To avoid conflict with a fixture named Update
from telegram import Message, User, Chat, CallbackQuery

@pytest.fixture
def mock_update():
    """Mocks the telegram.Update object."""
    update = MagicMock(spec=TelegramUpdate)
    
    # Mock user and chat objects
    mock_user = MagicMock(spec=User)
    mock_user.id = 12345
    mock_user.is_bot = False
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.username = "testuser"

    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 12345
    mock_chat.type = Chat.PRIVATE # Default to private chat

    # Mock message
    update.message = MagicMock(spec=Message)
    update.message.from_user = mock_user
    update.message.chat = mock_chat
    update.message.chat_id = mock_chat.id # Ensure chat_id is consistent
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    update.message.is_topic_message = False # Default
    update.message.message_thread_id = None # Default

    # Mock callback_query
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.data = ""
    update.callback_query.from_user = mock_user
    update.callback_query.message = MagicMock(spec=Message) # Callback message
    update.callback_query.message.chat = mock_chat
    update.callback_query.message.chat_id = mock_chat.id # Ensure chat_id is consistent
    update.callback_query.message.reply_text = AsyncMock()
    update.callback_query.message.edit_text = AsyncMock() # For editing messages
    update.callback_query.answer = AsyncMock()

    # Mock effective_chat as a PropertyMock if it's accessed directly as a property
    # For this fixture, we'll assume effective_chat is derived or set if needed by the test
    # If update.effective_chat is directly accessed, it might need to be:
    type(update).effective_chat = PropertyMock(return_value=mock_chat)
    
    return update

@pytest.fixture
def mock_context():
    """Mocks the telegram.ext.CallbackContext object."""
    context = MagicMock(spec=CallbackContext)
    context.bot = AsyncMock()
    context.args = []
    context.user_data = {} # For storing user-specific data
    context.chat_data = {} # For storing chat-specific data
    context.bot_data = {}  # For storing global bot data
    
    # Mock job queue if needed by any handlers
    context.job_queue = AsyncMock() 
    
    return context
