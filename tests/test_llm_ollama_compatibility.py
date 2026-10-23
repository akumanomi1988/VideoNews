"""Verify real Ollama SDK call signature without starting a network service.

This regression prevents passing an unsupported timeout= keyword to Client.chat.
Use a strict fake client exposing the documented Ollama Python API.
"""

import sys
import types

import pytest
from scripts.AI.natural_language_generation import LLMProvider


@pytest.mark.parametrize("timeout", [10, 60, 180])
def test_ollama_timeout_belongs_to_client_constructor(monkeypatch, timeout):
    created = []

    class OllamaClient:
        def __init__(self, host, *, timeout):
            created.append((host, timeout))

        def chat(self, model, messages, *, options, format):
            assert model == "fake-model"
            assert messages == [{"role": "user", "content": "Breaking news"}]
            assert options == {"num_predict": 123}
            assert format == "json"
            return {"message": {"content": '{"ok": true}'}}

    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=OllamaClient))
    provider = LLMProvider([{
        "type": "ollama", "model": "fake-model",
        "endpoint": "http://localhost:11434", "timeout": timeout,
    }])
    assert provider.available
    assert provider.complete("Breaking news", max_tokens=123) == '{"ok": true}'
    assert created == [("http://localhost:11434", timeout)]


def test_ollama_uses_default_client_timeout(monkeypatch):
    calls = []
    class Client:
        def __init__(self, host, *, timeout):
            calls.append(timeout)
        def chat(self, *, model, messages, options, format):
            return {"message": {"content": "{}"}}
    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=Client))
    provider = LLMProvider([{"type": "ollama", "model": "small-model"}])
    assert provider.complete("News") == "{}"
    assert calls == [60]


def test_ollama_failure_uses_next_configured_provider(monkeypatch):
    import sys
    class Broken:
        def __init__(self, host, *, timeout):
            pass
        def chat(self, **kwargs):
            raise ConnectionError("Ollama is not running")
    class GroqFake:
        def __init__(self, api_key):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(
                create=lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(content='{"source": "groq"}'))])
            ))
    monkeypatch.setitem(sys.modules, "ollama", types.SimpleNamespace(Client=Broken))
    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=GroqFake))
    provider = LLMProvider([{"type": "ollama", "model": "offline"},
                            {"type": "groq", "model": "backup", "api_key": "test-only"}])
    assert provider.complete("Current headlines") == '{"source": "groq"}'


def test_no_configured_llm_provider_fails_cleanly():
    provider = LLMProvider([])
    assert not provider.available
    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        provider.complete("News")
