"""Command-line entry point for the same rendering service used by Telegram.

Examples:
  python -m scripts.cli --title "Top technology story" --format short
  python -m scripts.cli --url https://example.com/news --format long
  python -m scripts.cli --text-file article.txt --format short
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="VideoNews video production")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--title", help="News topic or headline")
    source.add_argument("--url", help="Public article URL")
    source.add_argument("--text-file", type=Path, help="UTF-8 news article file")
    parser.add_argument("--format", choices=("short", "long"), default="short")
    parser.add_argument("--style", default=None, help="Image style (e.g. REALISM)")
    return parser.parse_args(argv)


async def run(args):
    from bot.services.video_service import VideoService

    service = VideoService()
    if args.url:
        handler = service.process_url_short if args.format == "short" else service.process_url_long
        return await handler(args.url)

    if args.text_file:
        text = args.text_file.read_text(encoding="utf-8").strip()
        if len(text) < 20:
            raise ValueError("Article must contain at least 20 characters")
        title, description = text[:100].split("\n", 1)[0], text
    else:
        title, description = args.title.strip(), ""
    if not title:
        raise ValueError("Article title cannot be empty")

    handler = service.process_short_news if args.format == "short" else service.process_long_news
    result = await handler(title, description, style=args.style.upper() if args.style else None)
    if not result:
        raise RuntimeError("Video generation did not complete")
    if result.get("local_path"):
        return result["local_path"]
    if result.get("platform") == "tiktok":
        return f"TikTok inbox: {result['publish_id']}"
    if result.get("id"):
        return f"https://www.youtube.com/watch?v={result['id']}"
    raise RuntimeError("Video generation yielded an invalid result")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except (OSError, RuntimeError, ValueError) as exc:
        logging.getLogger(__name__).exception("Production failed")
        print(f"ERROR: {exc}")
        return 1
    print(f"OUTPUT: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
