import requests
from colorama import Fore, init
from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil import parser as dateparser
from .interfaces import NewsProvider
from scripts.utils.file_cache import FileCache

init(autoreset=True)

ENGINE = "google_news"
BASE_URL = "https://serpapi.com/search"

CATEGORY_QUERIES = {
    'business': 'business news',
    'entertainment': 'entertainment news',
    'general': 'latest news',
    'health': 'health news',
    'science': 'science news',
    'sports': 'sports news',
    'technology': 'technology news',
}

GL_MAP = {
    'es': 'es', 'en': 'us', 'fr': 'fr', 'ru': 'ru', 'de': 'de',
    'it': 'it', 'pt': 'pt', 'ja': 'jp', 'zh': 'cn', 'ar': 'sa',
}

class SerpAPIProvider(NewsProvider):
    def __init__(self, api_key: str, use_cache: bool = True,
                 cache_ttl_hours: int = 24, cache_dir: str = ".temp/cache/serpapi"):
        self.api_key = api_key
        self.use_cache = use_cache
        self.cache = FileCache(cache_dir, ttl=cache_ttl_hours * 3600)

    def get_latest_news(self,
                       category: Optional[str] = None,
                       language: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        query = CATEGORY_QUERIES.get(category, "latest news") if category else "latest news"
        return self._search(query, language, limit)

    def search_news(self,
                   query: str,
                   language: Optional[str] = None,
                   category: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        return self._search(query, language, limit)

    def fetch_news(self, query: str, language: Optional[str] = None,
                   limit: int = 20, use_cache: Optional[bool] = None) -> List[Dict[str, Any]]:
        return self._search(query, language, limit, use_cache)

    @staticmethod
    def _normalize_lang(language: Optional[str]) -> str:
        lang = (language or 'es').strip()
        return lang.split('-')[0].split('_')[0].lower()

    def _search(self, query: str, language: Optional[str] = None,
                limit: int = 20, use_cache: Optional[bool] = None) -> List[Dict[str, Any]]:
        params = {
            'engine': ENGINE,
            'q': query,
            'api_key': self.api_key,
            'num': min(limit, 100),
        }

        lang = self._normalize_lang(language)
        gl = GL_MAP.get(lang)
        if gl:
            params['gl'] = gl
        params['hl'] = lang

        use_cache = use_cache if use_cache is not None else self.use_cache
        cache_key = self._cache_key(params)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                print(Fore.GREEN + f"SerpAPI cache hit for: {query}")
                return cached[:limit]

        print(Fore.CYAN + f"Fetching from SerpAPI: {query} (gl={gl}, hl={lang})")
        try:
            resp = requests.get(BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if 'news_results' not in data:
                print(Fore.YELLOW + f"SerpAPI returned no news_results: {data.get('error', 'unknown')}")
                return []

            articles = self._standardize_articles(data['news_results'])

            if use_cache and articles:
                self.cache.set(cache_key, articles)

            return articles[:limit]

        except requests.exceptions.Timeout:
            print(Fore.RED + "SerpAPI request timed out")
            return []
        except requests.exceptions.RequestException as e:
            error_data = getattr(e, 'response', None)
            if error_data is not None:
                try:
                    details = error_data.json()
                    print(Fore.RED + f"SerpAPI error: {details}")
                except Exception:
                    print(Fore.RED + f"SerpAPI error: {error_data.status_code} {error_data.reason}")
            else:
                print(Fore.RED + f"SerpAPI request failed: {e}")
            return []
        except Exception as e:
            print(Fore.RED + f"Unexpected SerpAPI error: {e}")
            return []

    def _standardize_articles(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for item in results:
            published = item.get('date', '')
            standardized.append({
                'title': item.get('title', ''),
                'url': item.get('link') or item.get('url', ''),
                'description': item.get('snippet', ''),
                'publishedAt': self._parse_serp_date(published),
                'source': item.get('source', 'Google News'),
                'content': item.get('snippet', ''),
                'author': item.get('author', ''),
            })
        return standardized

    @staticmethod
    def _parse_serp_date(date_str: str) -> Optional[str]:
        if not date_str:
            return None
        try:
            dt = dateparser.parse(date_str)
            return dt.isoformat()
        except Exception:
            return date_str

    @staticmethod
    def _cache_key(params: dict) -> str:
        relevant = {k: v for k, v in sorted(params.items()) if k != 'api_key'}
        return str(relevant)
