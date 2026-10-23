"""URL redirects, response bounds and HTML extraction; all network calls faked."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from scripts.DataFetcher import news_extractor as news

class Response:
    def __init__(self, status=200, *, headers=None, content=(b"<html>hi</html>",), encoding="utf-8"):
        self.status_code = status
        self.headers = headers or {}
        self.content = content
        self.encoding = encoding
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
    def raise_for_status(self):
        if self.status_code >= 400:
            raise news.requests.HTTPError(f"HTTP {self.status_code}")
    def iter_content(self, chunk_size):
        assert chunk_size <= news.MAX_HTML_BYTES
        yield from self.content

@pytest.fixture
def fakes(monkeypatch):
    calls = []
    urls = []
    def safe(url):
        urls.append(url)
        if url.startswith("http://internal."):
            raise ValueError("private network")
    monkeypatch.setattr(news, "validate_public_url", safe)
    fake_article = SimpleNamespace(
        title="Synthetic title", authors=["Editor"], text="Sample story",
        images={"https://example.org/pic.png"}, publish_date=None
    )
    class FakeArticle:
        def __init__(self, url):
            self.url = url
        def download(self, input_html):
            calls.append(("html", input_html))
        def parse(self):
            return None
        @property
        def title(self): return fake_article.title
        @property
        def authors(self): return fake_article.authors
        @property
        def text(self): return fake_article.text
        @property
        def images(self): return fake_article.images
        @property
        def publish_date(self): return fake_article.publish_date
    monkeypatch.setattr(news, "Article", FakeArticle)
    return calls, urls

def test_html_result_extracts_selected_fields(monkeypatch, fakes):
    response = Response(headers={"Content-Type": "text/html; charset=utf-8"})
    def get(url, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        assert kwargs["timeout"] == (10, 25)
        return response
    monkeypatch.setattr(news.requests, "get", get)
    result = news.NewsExtractor().extract_article("https://example.org/story")
    assert result.title == "Synthetic title"
    assert result.text == "Sample story"
    assert result.authors == ["Editor"]
    assert response.closed

@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_redirect_targets_are_revalidated(monkeypatch, fakes, code):
    calls, validated = fakes
    responses = [Response(status=code, headers={"Location": "/next"}),
                 Response(headers={"Content-Type": "text/html"})]
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: responses.pop(0))
    result = news.NewsExtractor().extract_article("https://example.org/start")
    assert result.text == "Sample story"
    assert validated == ["https://example.org/start", "https://example.org/next"]

def test_redirect_to_private_target_never_follows(monkeypatch, fakes):
    seen = []
    def get(*a, **k):
        seen.append(1)
        return Response(status=302, headers={"Location": "http://internal.example.org/secret"})
    monkeypatch.setattr(news.requests, "get", get)
    with pytest.raises(ValueError, match="private network"):
        news.NewsExtractor().extract_article("https://example.org/source")
    assert len(seen) == 1

def test_missing_redirect_location_rejected(monkeypatch, fakes):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(status=302))
    with pytest.raises(ValueError, match="Location"):
        news.NewsExtractor().extract_article("https://example.org")

def test_redirect_loop_has_hard_limit(monkeypatch, fakes):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return Response(status=302, headers={"Location": "/loop"})
    monkeypatch.setattr(news.requests, "get", get)
    with pytest.raises(ValueError, match="maximum number of redirects"):
        news.NewsExtractor().extract_article("https://example.org/loop")
    assert len(calls) == news.MAX_REDIRECTS + 1

@pytest.mark.parametrize("content_type", [
    "application/pdf", "image/png", "application/json", "text/plain"
])
def test_non_html_content_is_rejected(monkeypatch, fakes, content_type):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(headers={
        "Content-Type": content_type
    }))
    with pytest.raises(ValueError, match="return HTML"):
        news.NewsExtractor().extract_article("https://example.org/story")

def test_exact_html_size_limit_is_allowed(monkeypatch, fakes):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(
        content=[b"x" * news.MAX_HTML_BYTES]
    ))
    assert news.NewsExtractor().extract_article("https://example.org").text == "Sample story"

def test_html_larger_than_limit_is_rejected(monkeypatch, fakes):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(
        content=[b"a" * news.MAX_HTML_BYTES, b"overflow"]
    ))
    with pytest.raises(ValueError, match="2 MiB"):
        news.NewsExtractor().extract_article("https://example.org")

def test_upstream_http_status_error_bubbles(monkeypatch, fakes):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(status=503))
    with pytest.raises(news.requests.HTTPError):
        news.NewsExtractor().extract_article("https://example.org")

def test_parse_failure_is_gracefully_handled(monkeypatch, fakes):
    class BadArticle:
        def __init__(self, url): pass
        def download(self, input_html): raise news.ArticleException("broken")
    monkeypatch.setattr(news, "Article", BadArticle)
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response())
    assert news.NewsExtractor().extract_article("https://example.org") is None

def test_invalid_unicode_bytes_do_not_crash_decoder(monkeypatch, fakes):
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: Response(content=[b"\xff\xfe"]))
    assert news.NewsExtractor().extract_article("https://example.org").text == "Sample story"
