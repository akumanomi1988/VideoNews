"""Enroll or revoke automatic private publishing from a local owner console."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import private_publish_policy as policy
from scripts.studio_mcp import VideoNewsStudio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    enroll = actions.add_parser("enroll")
    enroll.add_argument("--max-uploads-per-day", type=int, default=2)
    actions.add_parser("revoke")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        parser.error("owner policy changes require an interactive local console")
    if args.action == "revoke":
        if input("Type exactly 'REVOKE PRIVATE AUTO-PUBLISH': ").strip() != "REVOKE PRIVATE AUTO-PUBLISH":
            print("Revocation cancelled.")
            return 1
        policy.revoke()
        print("Automatic private publishing revoked.")
        return 0

    if not 1 <= args.max_uploads_per_day <= 20:
        parser.error("--max-uploads-per-day must be 1-20")
    config = VideoNewsStudio._config()
    secrets_file = Path(config.get("youtube", {}).get("credentials_file", "")).expanduser().resolve()
    if not secrets_file.is_file():
        print("YouTube OAuth client secrets are not configured.", file=sys.stderr)
        return 2
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
    token_file = Path(config["youtube"].get("token_file", ".secrets/token.json")).expanduser().resolve()
    uploader = YoutubeMediaUploader(client_secrets_file=str(secrets_file),
                                    token_file=str(token_file))
    channel_id = uploader.get_channel_id()
    print(f"Channel verified: {channel_id}")
    print(f"Policy: PRIVATE only, up to {args.max_uploads_per_day} uploads per UTC day.")
    phrase = f"ENABLE PRIVATE AUTO-PUBLISH {channel_id} MAX {args.max_uploads_per_day}"
    if input(f"Type exactly '{phrase}' to enroll: ").strip() != phrase:
        print("Enrollment cancelled.")
        return 1
    policy.enroll(channel_id, args.max_uploads_per_day)
    print("Automatic private publishing enabled for this channel.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Publishing policy change failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
