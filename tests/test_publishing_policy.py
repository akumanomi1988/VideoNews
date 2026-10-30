"""Owner publishing policy validation and revocation."""
import json

import pytest

from scripts import publishing_policy as policy


def test_policy_persists_explicit_public_consent_channel_and_limit_and_revokes(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    enrolled = policy.enroll("UCchannel123", 3, privacy_status="public", public_consent=True)
    assert enrolled["privacy_status"] == "public"
    assert enrolled["allowed_privacy_statuses"] == ["public"]
    assert policy.load() == enrolled
    policy.revoke()
    assert policy.load() is None
    stored = json.loads(policy.policy_path().read_text(encoding="utf-8"))
    assert stored["enabled"] is False
    assert stored["channel_id"] == "UCchannel123"


@pytest.mark.parametrize("privacy", ["private", "unlisted"])
def test_owner_can_configure_non_public_default(tmp_path, monkeypatch, privacy):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    enrolled = policy.enroll("UCchannel123", 2, privacy_status=privacy)
    assert policy.load() == enrolled
    assert enrolled["allowed_privacy_statuses"] == [privacy]
    assert enrolled["public_consent"] is False


@pytest.mark.parametrize("channel_id,limit,privacy", [
    ("invalid", 2, "public"), ("UCchannel123", 0, "public"),
    ("UCchannel123", 21, "public"), ("UCchannel123", True, "public"),
    ("UCchannel123", 2, "invalid"),
])
def test_policy_rejects_invalid_enrollment(tmp_path, monkeypatch, channel_id, limit, privacy):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    with pytest.raises(ValueError):
        policy.enroll(channel_id, limit, privacy_status=privacy, public_consent=True)


def test_default_enrollment_is_private_and_public_requires_explicit_owner_consent(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    enrolled = policy.enroll("UCchannel123", 2)
    assert enrolled["privacy_status"] == "private"
    assert enrolled["allowed_privacy_statuses"] == ["private"]
    with pytest.raises(ValueError, match="Explicit owner consent"):
        policy.enroll("UCchannel123", 2, privacy_status="public")


def test_public_consent_binds_only_newssphere_channel(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    with pytest.raises(ValueError, match="NewSphere"):
        policy.enroll("UCchannel123", 2, public_consent=True,
                      channel_title="Different channel")


@pytest.mark.parametrize("tamper", [
    {"max_uploads_per_day": True},
    {"max_uploads_per_day": "2"},
    {"max_uploads_per_day": 0},
    {"allowed_privacy_statuses": ["public", "bogus"]},
    {"allowed_privacy_statuses": [["public"]]},
    {"allowed_privacy_statuses": ["private"]},
    {"public_consent": False},
])
def test_policy_fails_closed_when_persisted_policy_is_tampered(
        tmp_path, monkeypatch, tamper):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "policy"))
    policy.enroll("UCchannel123", 2, privacy_status="public", public_consent=True)
    data = json.loads(policy.policy_path().read_text(encoding="utf-8"))
    data.update(tamper)
    policy.policy_path().write_text(json.dumps(data), encoding="utf-8")
    assert policy.load() is None
