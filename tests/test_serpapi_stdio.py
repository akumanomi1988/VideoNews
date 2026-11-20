"""Search diagnostics must not replace or write to the MCP protocol stream."""
import importlib
import sys


def test_serpapi_import_and_repeated_cached_search_leave_stdout_alone(monkeypatch):
    class ProtocolStream:
        def write(self, value):
            raise OSError(22, "protocol stream cannot accept provider diagnostics")

        def flush(self):
            raise OSError(22, "protocol stream cannot be flushed by provider")

    stream = ProtocolStream()
    monkeypatch.setattr(sys, "stdout", stream)
    from scripts.DataFetcher import serpapi_client
    importlib.reload(serpapi_client)
    assert sys.stdout is stream
    provider = serpapi_client.SerpAPIProvider("test", use_cache=True)
    articles = [{"title": "Controlled cached article"}]
    monkeypatch.setattr(provider.cache, "get", lambda key: articles)
    for _ in range(3):
        assert provider.search_news("Spain", limit=1) == articles
        assert sys.stdout is stream
