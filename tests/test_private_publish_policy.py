"""Owner publishing policy validation and revocation."""
import json

import pytest

from scripts import private_publish_policy as policy


def test_policy_persists_channel_limit_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    enrolled = policy.enroll("UCchannel123", 3)
    assert policy.load() == enrolled
    policy.revoke()
    assert policy.load() is None
    stored = json.loads(policy.policy_path().read_text(encoding="utf-8"))
    assert stored["enabled"] is False
    assert stored["channel_id"] == "UCchannel123"


@pytest.mark.parametrize("channel_id,limit", [("invalid", 2), ("UCchannel123", 0),
                                                 ("UCchannel123", 21), ("UCchannel123", True)])
def test_policy_rejects_invalid_enrollment(tmp_path, monkeypatch, channel_id, limit):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    with pytest.raises(ValueError):
        policy.enroll(channel_id, limit)


@pytest.mark.parametrize("limit", [True, "2", 0, 21])
def test_policy_fails_closed_for_tampered_daily_limit(tmp_path, monkeypatch, limit):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    folder = policy.policy_path().parent
    folder.mkdir()
    policy.policy_path().write_text(json.dumps({
        "schema_version": 1, "enabled": True, "channel_id": "UCchannel123",
        "privacy_status": "private", "max_uploads_per_day": limit,
    }), encoding="utf-8")
    assert policy.load() is None
