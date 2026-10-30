"""Keep owner publishing consent and audit files outside the real user profile."""
import pytest


@pytest.fixture(autouse=True)
def isolated_owner_publishing_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_PUBLISH_POLICY_DIR", str(tmp_path / "owner-publishing-policy"))
