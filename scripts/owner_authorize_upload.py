"""Issue an exact, expiring YouTube upload grant from an interactive Windows console."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.studio_mcp import StudioError, VideoNewsStudio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id")
    parser.add_argument("--privacy-status", choices=("public", "private", "unlisted"),
                        default="private")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        parser.error("owner authorization requires an interactive local console")

    studio = VideoNewsStudio()
    project = studio.get_project(args.project_id)
    report = studio.review_video(args.project_id)
    if not report["ready_for_editorial_review"]:
        print("Review failed:")
        for issue in report["issues"]:
            print(f"- {issue}")
        return 2

    video = Path(project["video"]).resolve()
    metadata = project.get("youtube_metadata", {})
    print(f"Inspect the video in a player before approving this {args.privacy_status} upload.")
    print(f"Project: {project['id']}\nTitle: {metadata.get('title', project['title'])}")
    print(f"Video: {video}\nSHA-256: {studio._hash(video)}")
    print(f"Target privacy: {args.privacy_status.upper()}\nDuration: {report['duration_seconds']} seconds")
    video_hash = studio._hash(video)
    expected = (f"APPROVE {args.privacy_status.upper()} UPLOAD {project['id']} "
                f"SHA256 {video_hash}")
    if input(f"Type exactly '{expected}' after reviewing the video: ").strip() != expected:
        print("Approval cancelled.")
        return 1

    config = studio._config()
    source = Path(config["youtube"]["credentials_file"]).resolve()
    if not source.is_file():
        print("YouTube OAuth client secrets are not configured.")
        return 2
    from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
    token_file = Path(config["youtube"].get("token_file", ".secrets/token.json")).resolve()
    uploader = YoutubeMediaUploader(client_secrets_file=str(source),
                                    token_file=str(token_file))
    channel = uploader.get_channel_info()
    channel_id = channel["id"]
    if args.privacy_status == "public" and channel["title"].strip().casefold() != "newsphere":
        print("Public one-use grants are restricted to the NewSphere channel.")
        return 3
    grant = studio.issue_owner_authorization(
        project["id"], owner_confirmed=True, target_account_id=channel_id,
        privacy_status=args.privacy_status)
    print(f"One-use {args.privacy_status} upload authorization issued for channel {channel_id}.")
    print(f"It expires in {grant['expires_in_seconds']} seconds; return to the studio to upload.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (StudioError, OSError, ValueError) as exc:
        print(f"Authorization failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
