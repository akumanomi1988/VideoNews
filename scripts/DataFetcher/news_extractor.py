"""Bounded HTML news extraction with validated redirect targets."""
from __future__ import annotations

from urllib.parse import urljoin

import requests
from newspaper import Article
from newspaper.article import ArticleException

from scripts.url_safety import validate_public_url

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5


class ArticleData:
    def __init__(self, title, authors, text, images, publish_date):
        self.title = title
        self.authors = authors
        self.text = text
        self.images = images
        self.publish_date = publish_date

    def __str__(self):
        return (
            f"Title: {self.title}\nAuthors: {', '.join(self.authors)}\n"
            f"Date: {self.publish_date}\nText: {self.text[:500]}..."
        )


class NewsExtractor:
    def extract_article(self, url: str):
        target = url
        for _ in range(MAX_REDIRECTS + 1):
            validate_public_url(target)
            with requests.get(
                target,
                headers={"User-Agent": "VideoNews/1.0 (article extraction)"},
                timeout=(10, 25),
                allow_redirects=False,
                stream=True,
            ) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        raise ValueError("Article redirect did not include a Location")
                    target = urljoin(target, location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    raise ValueError("Article URL did not return HTML")
                chunks = []
                total = 0
                for part in response.iter_content(chunk_size=65536):
                    total += len(part)
                    if total > MAX_HTML_BYTES:
                        raise ValueError("Article HTML exceeds 2 MiB size limit")
                    chunks.append(part)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
            try:
                article = Article(target)
                article.download(input_html=html)
                article.parse()
                return ArticleData(
                    title=article.title,
                    authors=article.authors,
                    text=article.text,
                    images=list(article.images),
                    publish_date=article.publish_date,
                )
            except ArticleException:
                return None
        raise ValueError("Article exceeded the maximum number of redirects")
