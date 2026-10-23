"""Denied users cannot invoke Telegram mutations or leak callback data."""
from types import SimpleNamespace
import pytest
from bot.auth import allowed_user_ids, is_authorized, protected

@pytest.mark.parametrize("raw,expected", [
    ("", frozenset()), (" ", frozenset()), ("42", frozenset({42})),
    (" 42 , 100 , 42 ", frozenset({42, 100}))
])
def test_numeric_allowlist_format(monkeypatch, raw, expected):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", raw)
    assert allowed_user_ids() == expected

@pytest.mark.parametrize("bad", ["alice", "123,admin", "2.5", "0xFF"])
def test_invalid_user_id_disables_all_access(monkeypatch, bad):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", bad)
    assert not is_authorized(123)
    assert allowed_user_ids() == frozenset()

def test_none_user_cannot_be_authorized(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "99")
    assert not is_authorized(None)

@pytest.mark.asyncio
async def test_unauthorized_callback_is_acknowledged_and_handler_not_called(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "99")
    calls = []
    answers = []
    async def handler(update, context):
        calls.append("invoked")
    async def answer(text, show_alert=False):
        answers.append((text, show_alert))
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=5),
        callback_query=SimpleNamespace(answer=answer),
        effective_message=None,
    )
    assert await protected(handler)(update, None) is None
    assert calls == []
    assert answers == [("Not authorized", True)]

@pytest.mark.asyncio
async def test_no_effective_user_is_denied_without_crashing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "99")
    async def handler(update, context):
        pytest.fail("Never invoke handler")
    await protected(handler)(SimpleNamespace(
        effective_user=None, callback_query=None, effective_message=None
    ), None)

@pytest.mark.asyncio
async def test_authorized_handler_receives_same_context_and_result(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "99")
    expected = object()
    context = object()
    async def handler(update, received):
        assert received is context
        assert update.effective_user.id == 99
        return expected
    wrapped = protected(handler)
    update = SimpleNamespace(effective_user=SimpleNamespace(id=99))
    assert await wrapped(update, context) is expected
    assert wrapped.__name__ == "handler"
