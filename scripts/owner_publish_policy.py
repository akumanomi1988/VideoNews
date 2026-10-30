"""Enroll or revoke automatic YouTube publishing from the local owner console."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts import publishing_policy as policy
from scripts.studio_mcp import VideoNewsStudio


def _backup_token(token_file: Path) -> None:
    """Preserve any previous OAuth token before a new consent flow can write."""
    candidates = [token_file]
    legacy = token_file.parent / "_token.json"
    if legacy.is_file() and legacy.resolve() != token_file.resolve():
        candidates.append(legacy)
    backup_dir = token_file.parent / "backups"
    for source in candidates:
        if not source.is_file():
            continue
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = backup_dir / f"{source.stem}-{stamp}{source.suffix}.bak"
        shutil.copy2(source, destination)
        if sys.platform == "win32":
            import subprocess
            subprocess.run(["icacls", str(destination), "/inheritance:r", "/grant:r",
                            f"*{policy._current_sid()}:(F)"], check=True,
                           capture_output=True, text=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    enroll = actions.add_parser("enroll")
    enroll.add_argument("--max-uploads-per-day", type=int, default=2)
    enroll.add_argument("--privacy-status", choices=policy.PRIVACY_STATUSES,
                        default="private")
    enroll.add_argument("--allow-privacy-status", action="append",
                        choices=policy.PRIVACY_STATUSES,
                        help="Allow an additional per-video status; may be repeated")
    actions.add_parser("revoke")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        parser.error("owner policy changes require an interactive local console")
    if args.action == "revoke":
        if input("Type exactly 'REVOKE AUTOMATIC YOUTUBE PUBLISHING': ").strip() != "REVOKE AUTOMATIC YOUTUBE PUBLISHING":
            print("Revocation cancelled.")
            return 1
        policy.revoke()
        print("Automatic YouTube publishing revoked.")
        return 0

    if not 1 <= args.max_uploads_per_day <= 20:
        parser.error("--max-uploads-per-day must be 1-20")
    config = VideoNewsStudio._config()
    secrets_file = Path(config.get("youtube", {}).get("credentials_file", "")).expanduser().resolve()
    if not secrets_file.is_file():
        print("YouTube OAuth client secrets are not configured.", file=sys.stderr)
        return 2
    token_file = Path(config["youtube"].get("token_file", ".secrets/token.json")).expanduser().resolve()
    _backup_token(token_file)
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
    uploader = YoutubeMediaUploader(client_secrets_file=str(secrets_file),
                                    token_file=str(token_file))
    channel = uploader.get_channel_info()
    channel_id = channel["id"]
    if channel["title"].strip().casefold() != "newsphere":
        print(f"Authenticated channel is '{channel['title']}', not NewSphere; enrollment refused.",
              file=sys.stderr)
        return 3
    allowed = list(dict.fromkeys(args.allow_privacy_status or [args.privacy_status]))
    if args.privacy_status not in allowed:
        allowed.insert(0, args.privacy_status)
    public_consent = "public" in allowed
    allowed_label = ",".join(allowed)
    print(f"Channel verified: {channel['title']} ({channel_id})")
    print(f"Default privacy: {args.privacy_status}; allowed: {allowed_label}; "
          f"limit: {args.max_uploads_per_day} per UTC day.")
    if public_consent:
        print("This enables automatic PUBLIC publishing after each explicit ChatGPT upload request.")
    phrase = (f"ENABLE YOUTUBE AUTO-PUBLISH {channel_id} DEFAULT {args.privacy_status.upper()} "
              f"ALLOW {allowed_label.upper()} MAX {args.max_uploads_per_day}")
    if input(f"Type exactly '{phrase}' to enroll: ").strip() != phrase:
        print("Enrollment cancelled.")
        return 1
    policy.enroll(channel_id, args.max_uploads_per_day,
                  privacy_status=args.privacy_status,
                  allowed_privacy_statuses=allowed,
                  public_consent=public_consent,
                  channel_title=channel["title"])
    print(f"Automatic YouTube publishing enabled for {channel['title']}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Publishing policy change failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
