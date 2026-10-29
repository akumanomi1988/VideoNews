"""Owner-only policy storage for automatic PRIVATE YouTube publishing."""
from __future__ import annotations

import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _directory() -> Path:
    configured = os.getenv("VIDEO_PUBLISH_POLICY_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return root / "VideoNews"


def _secure_directory(path: Path) -> None:
    if os.name != "nt":
        return
    sid = _current_sid()
    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                    f"*{sid}:(OI)(CI)F"], check=True, capture_output=True, text=True)


def policy_path() -> Path:
    return _directory() / "private-publishing.json"


def audit_path() -> Path:
    return _directory() / "private-publishing-audit.jsonl"


def load() -> dict | None:
    try:
        data = json.loads(policy_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Automatic publishing policy is unreadable") from exc
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or data.get("enabled") is not True
            or not isinstance(data.get("channel_id"), str)
            or type(data.get("max_uploads_per_day")) is not int
            or not 1 <= data["max_uploads_per_day"] <= 20):
        return None
    return data


def enroll(channel_id: str, max_uploads_per_day: int) -> dict:
    if not isinstance(channel_id, str) or not channel_id.startswith("UC"):
        raise ValueError("Invalid YouTube channel ID")
    if type(max_uploads_per_day) is not int or not 1 <= max_uploads_per_day <= 20:
        raise ValueError("max_uploads_per_day must be 1-20")
    folder = _directory()
    folder.mkdir(parents=True, exist_ok=True)
    _secure_directory(folder)
    policy = {"schema_version": 1, "enabled": True, "channel_id": channel_id,
              "privacy_status": "private", "max_uploads_per_day": max_uploads_per_day,
              "enrolled_at": datetime.now(timezone.utc).isoformat()}
    path = policy_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    if os.name == "nt":
        subprocess.run(["icacls", str(temporary), "/inheritance:r", "/grant:r",
                        f"*{_current_sid()}:(F)"], check=True, capture_output=True, text=True)
    temporary.replace(path)
    return policy


def _current_sid() -> str:
    who = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                         check=True, capture_output=True, text=True)
    return next(csv.reader(who.stdout.splitlines()))[-1]


def revoke() -> None:
    path = policy_path()
    if not path.is_file():
        return
    policy = json.loads(path.read_text(encoding="utf-8"))
    policy.update(enabled=False, revoked_at=datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(policy, indent=2), encoding="utf-8")


def audit(project_id: str, video_sha256: str, channel_id: str,
          outcome: str, video_id: str = "") -> None:
    folder = _directory()
    folder.mkdir(parents=True, exist_ok=True)
    _secure_directory(folder)
    record = {"at": datetime.now(timezone.utc).isoformat(), "project_id": project_id,
              "video_sha256": video_sha256, "channel_id": channel_id,
              "video_id": video_id, "outcome": outcome}
    with audit_path().open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")


def records() -> list[dict]:
    path = audit_path()
    if not path.is_file():
        return []
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Automatic publishing audit log is unreadable") from exc
