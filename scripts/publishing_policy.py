"""Owner-only, channel-bound policy for automatic YouTube publishing."""
from __future__ import annotations

import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PRIVACY_STATUSES = ("public", "private", "unlisted")


def _directory() -> Path:
    configured = os.getenv("VIDEO_PUBLISH_POLICY_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return root / "VideoNews"


def _current_sid() -> str:
    who = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                         check=True, capture_output=True, text=True)
    return next(csv.reader(who.stdout.splitlines()))[-1]


def _secure_file(path: Path) -> None:
    if os.name == "nt":
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        f"*{_current_sid()}:(F)"], check=True,
                       capture_output=True, text=True)


def _secure_directory(path: Path) -> None:
    if os.name == "nt":
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        f"*{_current_sid()}:(OI)(CI)F"], check=True,
                       capture_output=True, text=True)


def policy_path() -> Path:
    return _directory() / "publishing-policy.json"


def audit_path() -> Path:
    return _directory() / "publishing-audit.jsonl"


def load() -> dict | None:
    try:
        data = json.loads(policy_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Automatic publishing policy is unreadable") from exc
    allowed = data.get("allowed_privacy_statuses") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or data.get("schema_version") != 2
            or data.get("enabled") is not True
            or not isinstance(data.get("channel_id"), str)
            or not data["channel_id"].startswith("UC")
            or data.get("privacy_status") not in PRIVACY_STATUSES
            or not isinstance(allowed, list) or not allowed
            or any(not isinstance(s, str) for s in allowed)
            or any(s not in PRIVACY_STATUSES for s in allowed)
            or len(set(allowed)) != len(allowed)
            or data["privacy_status"] not in allowed
            or type(data.get("public_consent")) is not bool
            or ("public" in allowed and data["public_consent"] is not True)
            or type(data.get("max_uploads_per_day")) is not int
            or not 1 <= data["max_uploads_per_day"] <= 20):
        return None
    return data


def enroll(channel_id: str, max_uploads_per_day: int,
           privacy_status: str = "private",
           allowed_privacy_statuses: list[str] | None = None,
           *, public_consent: bool = False,
           channel_title: str = "NewSphere") -> dict:
    if not isinstance(channel_id, str) or not channel_id.startswith("UC"):
        raise ValueError("Invalid YouTube channel ID")
    if type(max_uploads_per_day) is not int or not 1 <= max_uploads_per_day <= 20:
        raise ValueError("max_uploads_per_day must be 1-20")
    if privacy_status not in PRIVACY_STATUSES:
        raise ValueError("privacy_status must be public, private, or unlisted")
    allowed = list(allowed_privacy_statuses or [privacy_status])
    if (not allowed or any(s not in PRIVACY_STATUSES for s in allowed)
            or len(set(allowed)) != len(allowed) or privacy_status not in allowed):
        raise ValueError("Allowed privacy statuses must be unique and include the default")
    if "public" in allowed and public_consent is not True:
        raise ValueError("Explicit owner consent is required to enable public publishing")
    if not isinstance(channel_title, str) or channel_title.strip().casefold() != "newsphere":
        raise ValueError("Automatic publishing can only enroll the NewSphere channel")
    folder = _directory()
    folder.mkdir(parents=True, exist_ok=True)
    _secure_directory(folder)
    policy = {"schema_version": 2, "enabled": True, "channel_id": channel_id,
              "channel_title": channel_title.strip(),
              "privacy_status": privacy_status,
              "allowed_privacy_statuses": allowed,
              "public_consent": "public" in allowed and public_consent is True,
              "max_uploads_per_day": max_uploads_per_day,
              "enrolled_at": datetime.now(timezone.utc).isoformat()}
    path = policy_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    _secure_file(temporary)
    temporary.replace(path)
    return policy


def revoke() -> None:
    path = policy_path()
    if not path.is_file():
        return
    policy = json.loads(path.read_text(encoding="utf-8"))
    policy.update(enabled=False, revoked_at=datetime.now(timezone.utc).isoformat())
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    _secure_file(temporary)
    temporary.replace(path)


def audit(project_id: str, video_sha256: str, channel_id: str,
          outcome: str, video_id: str = "", privacy_status: str = "") -> None:
    folder = _directory()
    folder.mkdir(parents=True, exist_ok=True)
    _secure_directory(folder)
    record = {"at": datetime.now(timezone.utc).isoformat(), "project_id": project_id,
              "video_sha256": video_sha256, "channel_id": channel_id,
              "video_id": video_id, "privacy_status": privacy_status,
              "outcome": outcome}
    with audit_path().open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    _secure_file(audit_path())


def records() -> list[dict]:
    path = audit_path()
    if not path.is_file():
        return []
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Automatic publishing audit log is unreadable") from exc
