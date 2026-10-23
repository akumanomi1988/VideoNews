from types import SimpleNamespace

import pytest

from bot.auth import allowed_user_ids, is_authorized, protected


def test_authorization_is_closed_by_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    assert allowed_user_ids() == frozenset()
    assert not is_authorized(123)


@pytest.mark.asyncio
async def test_protected_handler_only_invokes_authorized_user(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "42, 77")
    invoked = []
    replies = []

    async def target(update, context):
        invoked.append(update.effective_user.id)

    async def reply(text):
        replies.append(text)

    guarded = protected(target)
    denied = SimpleNamespace(
        effective_user=SimpleNamespace(id=7), callback_query=None,
        effective_message=SimpleNamespace(reply_text=reply),
    )
    allowed = SimpleNamespace(effective_user=SimpleNamespace(id=42))
    await guarded(denied, None)
    await guarded(allowed, None)
    assert invoked == [42]
    assert replies == ["Not authorized."]


def test_invalid_allowlist_fails_closed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "123,nope")
    assert not is_authorized(123)
