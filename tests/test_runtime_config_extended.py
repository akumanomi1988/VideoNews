"""Configuration precedence, validation and secret handling."""
import json
import pytest
from scripts.runtime_config import load_runtime_config

@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in (
        "SERPAPI_API_KEY", "PEXELS_API_KEY", "NEWS_API_KEY", "CURRENTS_API_KEY",
        "GROQ_API_KEY", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
        "OLLAMA_MODEL", "VIDEO_TEMP_DIR", "MEDIA_SOURCE", "TTS_VOICE",
        "OLLAMA_ENABLED", "YOUTUBE_CLIENT_SECRETS_FILE", "SERPAPI_USE_CACHE", "SERPAPI_CACHE_TTL_HOURS"
    ):
        monkeypatch.delenv(key, raising=False)

def _settings(tmp_path, data):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)

def test_defaults_are_isolated_between_calls():
    first = load_runtime_config()
    first["serpapi"]["api_key"] = "changed"
    first["llm"]["providers"].append({"type": "bad"})
    second = load_runtime_config()
    assert second["serpapi"]["api_key"] == ""
    assert all(item["type"] != "bad" for item in second["llm"]["providers"])

def test_partial_nested_override_keeps_other_default_fields(tmp_path):
    path = _settings(tmp_path, {"settings": {"parallel_workers": 1}})
    loaded = load_runtime_config(path)
    assert loaded["settings"]["parallel_workers"] == 1
    assert loaded["settings"]["media_source"] == "pexels"

def test_invalid_root_rejected(tmp_path):
    path = _settings(tmp_path, [1, 2, 3])
    with pytest.raises(ValueError, match="JSON object"):
        load_runtime_config(path)

def test_malformed_json_fails_explicitly(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{unclosed", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_runtime_config(str(path))

@pytest.mark.parametrize("legacy_field,section", [
    ("news_api", "newsapi"), ("pexels_api", "pexels")
])
def test_legacy_api_keys_are_mapped(tmp_path, legacy_field, section):
    path = _settings(tmp_path, {"api_keys": {legacy_field: "legacy"}})
    assert load_runtime_config(path)[section]["api_key"] == "legacy"

def test_legacy_oauth_credential_path_is_mapped(tmp_path):
    path = _settings(tmp_path, {"oauth": {"youtube": {"credentials_file": "private.json"}}})
    assert load_runtime_config(path)["youtube"]["credentials_file"] == "private.json"

@pytest.mark.parametrize("env,section,field", [
    ("SERPAPI_API_KEY", "serpapi", "api_key"),
    ("PEXELS_API_KEY", "pexels", "api_key"),
    ("NEWS_API_KEY", "newsapi", "api_key"),
    ("CURRENTS_API_KEY", "currentsapi", "api_key"),
    ("VIDEO_TEMP_DIR", "settings", "temp_dir"),
    ("MEDIA_SOURCE", "settings", "media_source"),
    ("TTS_VOICE", "tts_edge", "voice"),
])
def test_runtime_environment_has_highest_precedence(monkeypatch, env, section, field):
    monkeypatch.setenv(env, "env-only")
    assert load_runtime_config()[section][field] == "env-only"

@pytest.mark.parametrize("raw,enabled", [
    ("true", True), ("TRUE", True), ("yes", True), ("1", True),
    ("false", False), ("0", False), ("no", False), ("other", False),
])
def test_cache_toggle_is_parsed_as_boolean(monkeypatch, raw, enabled):
    monkeypatch.setenv("SERPAPI_USE_CACHE", raw)
    assert load_runtime_config()["serpapi"]["use_cache"] is enabled

@pytest.mark.parametrize("raw,parsed", [("0", 0), ("24", 24), ("120", 120)])
def test_cache_ttl_is_numeric(monkeypatch, raw, parsed):
    monkeypatch.setenv("SERPAPI_CACHE_TTL_HOURS", raw)
    assert load_runtime_config()["serpapi"]["cache_ttl_hours"] == parsed

@pytest.mark.parametrize("raw", ["none", "3.5", "1h", ""])
def test_cache_ttl_rejects_invalid_integer(monkeypatch, raw):
    monkeypatch.setenv("SERPAPI_CACHE_TTL_HOURS", raw)
    with pytest.raises(ValueError, match="must be an integer"):
        load_runtime_config()

def test_disabled_ollama_and_no_other_providers_yield_empty_failover(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    assert load_runtime_config()["llm"]["providers"] == []

def test_groq_provider_fallback_has_environment_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    monkeypatch.setenv("GROQ_API_KEY", "secret-groq")
    provider = load_runtime_config()["llm"]["providers"][0]
    assert provider["type"] == "groq"
    assert provider["api_key"] == "secret-groq"

def test_azure_requires_both_endpoint_and_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.azure.com")
    assert load_runtime_config()["llm"]["providers"] == []
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret")
    assert load_runtime_config()["llm"]["providers"][0]["type"] == "azure"

def test_explicit_llm_provider_list_is_preserved(tmp_path, monkeypatch):
    path = _settings(tmp_path, {"llm": {"providers": [{"type": "custom", "endpoint": "https://example.org"}]}})
    monkeypatch.setenv("GROQ_API_KEY", "another-provider")
    assert load_runtime_config(path)["llm"]["providers"] == [
        {"type": "custom", "endpoint": "https://example.org"}
    ]

def test_environment_secret_is_not_persisted_in_settings(tmp_path, monkeypatch):
    path = _settings(tmp_path, {"serpapi": {"api_key": ""}})
    monkeypatch.setenv("SERPAPI_API_KEY", "never-write-me")
    assert load_runtime_config(path)["serpapi"]["api_key"] == "never-write-me"
    assert "never-write-me" not in (tmp_path / "settings.json").read_text()
