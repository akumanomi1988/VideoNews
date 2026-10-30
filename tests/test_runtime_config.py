import pytest

from scripts.runtime_config import load_runtime_config


def test_defaults_do_not_require_a_settings_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    config = load_runtime_config()
    assert config["settings"]["media_source"] == "huggingface"
    assert config["serpapi"]["api_key"] == ""
    assert config["youtube"]["credentials_file"]


def test_environment_overrides_legacy_json(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.json"
    config_path.write_text('{"serpapi": {"api_key": "OLD"}, "settings": {"temp_dir": ".old"}}')
    monkeypatch.setenv("SERPAPI_API_KEY", "NEW")
    monkeypatch.setenv("VIDEO_TEMP_DIR", "job-temp")
    config = load_runtime_config(str(config_path))
    assert config["serpapi"]["api_key"] == "NEW"
    assert config["settings"]["temp_dir"] == "job-temp"
    assert "NEW" not in config_path.read_text()


def test_explicit_missing_file_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_runtime_config(str(tmp_path / "does-not-exist.json"))
