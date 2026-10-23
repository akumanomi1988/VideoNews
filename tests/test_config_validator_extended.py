"""Validator recursion, input types, allowed values and filesystem checks."""
import json
import pytest
from scripts.config_validator import ConfigValidator, ValidationError

@pytest.fixture
def validator():
    return ConfigValidator()

@pytest.mark.parametrize("value", [
    None, "", 123, [], "wrong", True
])
def test_config_root_must_be_mapping(validator, value):
    errors = validator.validate(value)
    assert any("Expected type dict" in error.message for error in errors)

def test_required_top_level_fields_are_reported(validator):
    errors = validator.validate({})
    paths = {error.path for error in errors}
    assert {"api_keys", "oauth", "database", "pipeline", "video", "tts", "news", "media", "upload"} <= paths

def test_nested_required_fields_identified_by_full_path(validator):
    errors = validator._validate_field({}, {
        "type": dict, "fields": {"article": {"type": dict, "required": True,
            "fields": {"language": {"type": str, "required": True}}}}
    }, "")
    assert [e.path for e in errors] == ["article"]

def test_nested_invalid_field_type_is_reported(validator):
    errors = validator._validate_field({"article": {"language": 77}}, {
        "type": dict, "fields": {"article": {"type": dict, "required": True,
            "fields": {"language": {"type": str, "required": True}}}}
    }, "")
    assert errors[0].path == "article.language"
    assert "Expected type str" in errors[0].message

@pytest.mark.parametrize("value", ["private", "public", "unlisted"])
def test_enum_accepts_known_values(validator, value):
    errors = validator._validate_field(value, {"type": str, "values": [
        "private", "public", "unlisted"
    ]}, "youtube.privacy")
    assert errors == []

@pytest.mark.parametrize("value", ["PUBLIC", "anonymous", "friends", ""])
def test_enum_rejects_invalid_values(validator, value):
    errors = validator._validate_field(value, {"type": str, "values": [
        "private", "public", "unlisted"
    ]}, "youtube.privacy")
    assert errors[0].path == "youtube.privacy"

@pytest.mark.parametrize("resolution", ["1920x1080", "1080x1920", "360x640"])
def test_resolution_regex_accepts_standard_geometry(validator, resolution):
    assert validator._validate_field(resolution, {"type": str, "pattern": r"^\d+x\d+$"}, "video.resolution") == []

@pytest.mark.parametrize("resolution", ["1080*1920", "HD", "1920X1080", "1920x"])
def test_resolution_regex_rejects_non_numeric_dimensions(validator, resolution):
    assert validator._validate_field(resolution, {"type": str, "pattern": r"^\d+x\d+$"}, "video.resolution")

def test_invalid_json_produces_file_error(validator, tmp_path):
    file = tmp_path / "invalid.json"
    file.write_text("{bad json", encoding="utf-8")
    errors = validator.validate_file(str(file))
    assert len(errors) == 1
    assert errors[0].path == "file"

def test_missing_file_produces_file_error(validator, tmp_path):
    errors = validator.validate_file(str(tmp_path / "missing.json"))
    assert errors[0].path == "file"

def test_valid_empty_schema_can_be_formatted(validator):
    assert validator.format_errors([]) == "Configuration is valid"

def test_validation_errors_have_readable_paths(validator):
    formatted = validator.format_errors([ValidationError(path="tts.voice", message="Missing required field")])
    assert "tts.voice" in formatted
    assert "Missing required field" in formatted

def test_file_when_directory_required_is_reported(validator, tmp_path):
    path = tmp_path / "not-a-directory"
    path.write_text("data", encoding="utf-8")
    errors = validator.verify_paths({"pipeline": {"temp_dir": str(path)}})
    assert any(e.path == "pipeline.temp_dir" for e in errors)

def test_existing_directory_does_not_raise_a_path_error(validator, tmp_path):
    assert validator.verify_paths({"pipeline": {"temp_dir": str(tmp_path)}}) == []
