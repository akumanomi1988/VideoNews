"""Local-only operations for jobs whose external upload status is uncertain.

Usage:
  python -m scripts.jobs_cli pending
  python -m scripts.jobs_cli inspect https://example.com/story
  python -m scripts.jobs_cli resolve https://example.com/story --published --reference VIDEO_URL --confirm VERIFIED
  python -m scripts.jobs_cli resolve https://example.com/story --not-published --confirm VERIFIED

Never retry an uncertain publication until the platform was checked manually.
"""
from __future__ import annotations

import argparse
import json

from scripts.job_registry import get, reconcile, review_required


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="VideoNews durable job registry operations")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("pending", help="List non-terminal jobs")
    inspect = actions.add_parser("inspect", help="Inspect one URL")
    inspect.add_argument("url")
    resolve = actions.add_parser("resolve", help="Manually resolve uncertain outcome")
    resolve.add_argument("url")
    group = resolve.add_mutually_exclusive_group(required=True)
    group.add_argument("--published", action="store_true", help="Video definitely exists remotely")
    group.add_argument("--not-published", action="store_true", help="No remote upload exists")
    resolve.add_argument("--reference", help="Confirmed remote video URL or identifier")
    resolve.add_argument("--confirm", choices=["VERIFIED"], required=True)
    args = parser.parse_args(argv)

    if args.action == "pending":
        print(json.dumps(review_required(), indent=2))
        return 0
    if args.action == "inspect":
        print(json.dumps(get(args.url), indent=2))
        return 0 if get(args.url) else 1

    reconcile(args.url, published=args.published, reference=args.reference or "")
    print(json.dumps(get(args.url), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
