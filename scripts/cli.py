"""Command-line fallback for deterministic local video production.

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
    from news_video_processor import NewsVideoProcessor
    from scripts.DataFetcher.news_extractor import NewsExtractor

    processor = NewsVideoProcessor()
    if args.url:
        article = NewsExtractor().extract_article(args.url)
        if not article or len(article.text.strip()) < 20:
            raise ValueError("Could not extract enough article text from the provided URL")
        title, description = article.title, article.text
        source_url = args.url

    elif args.text_file:
        text = args.text_file.read_text(encoding="utf-8").strip()
        if len(text) < 20:
            raise ValueError("Article must contain at least 20 characters")
        title, description = text[:100].split("\n", 1)[0], text
        source_url = ""
    else:
        title, description = args.title.strip(), ""
        source_url = ""
    if not title:
        raise ValueError("Article title cannot be empty")

    news = {"title": title[:240], "description": description, "source": source_url or description}
    if args.style:
        news["style"] = args.style.upper()
    handler = (processor.process_latest_news_in_short_format if args.format == "short"
               else processor.process_latest_news_in_long_format)
    result = await asyncio.to_thread(handler, news)
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
