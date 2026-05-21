import json
import spacy
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor, Future
from dateutil import parser
from fake_useragent import UserAgent
from newspaper import Article
from newsapi import NewsApiClient
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential
from textblob import TextBlob
from urllib3.util.retry import Retry
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import textstat

from scripts.DataFetcher.news_mapper import parse_rss_to_standard_object

# --- Constants ---
DEFAULT_VIRAL_NEWS_FILE = 'viral_news.json'
DEFAULT_TIME_WINDOW_DAYS = 2
DEFAULT_VIRALITY_THRESHOLD = 0.5
DEFAULT_MAX_WORKERS = 5
DEFAULT_RSS_TIMEOUT = 10
DEFAULT_ARTICLE_TIMEOUT = 10
DEFAULT_NEWSAPI_COUNTRIES = ['es', 'us', 'gb', 'fr', 'ru']
DEFAULT_CURRENTS_LANGUAGES = ['es', 'en', 'fr', 'ru']
PUB_DATE_FIELDS = ['pub_date', 'pubDate', 'published', 'updated', 'dc:date', 'lastBuildDate']

# --- Initialize colorama ---
init(autoreset=True)

# --- Load spaCy model ---
def load_spacy_model(model_name: str = "es_core_news_sm"):
    """Load or download the specified spaCy model."""
    try:
        return spacy.load(model_name)
    except OSError:
        print(Fore.RED + f"Modelo {model_name} not found. Downloading...")
        import spacy.cli
        spacy.cli.download(model_name)
        return spacy.load(model_name)

nlp = load_spacy_model()

class NewsProcessor:
    """
    Processes news articles from various sources, evaluates their virality,
    and stores viral news for later retrieval.
    """
    def __init__(self, config: Dict[str, Any], viral_news_file: str = DEFAULT_VIRAL_NEWS_FILE):
        self._config = config
        self._viral_news_file = viral_news_file
        self._processed_news: List[Dict[str, Any]] = []
        self._news_index = 0
        self._ua = UserAgent()
        self._vader_analyzer = SentimentIntensityAnalyzer()
        self._load_viral_news()

    def process_all_news(self) -> None:
        """
        Processes all news from configured sources, evaluates virality,
        and stores the results.
        """
        all_news = []
        successful_sources = 0
        total_sources = 0

        # Process RSS feeds
        for feed_url in self._config.get('rss_feeds', []):
            total_sources += 1
            news_items = self._process_rss_feed(feed_url)
            if news_items:
                all_news.extend(news_items)
                successful_sources += 1

        # Process NewsAPI
        total_sources += 1
        newsapi_news = self._process_newsapi()
        if newsapi_news:
            all_news.extend(newsapi_news)
            successful_sources += 1

        # Process CurrentsAPI
        total_sources += 1
        currents_news = self._process_currentsapi()
        if currents_news:
            all_news.extend(currents_news)
            successful_sources += 1

        # Evaluate virality in parallel
        print(Fore.CYAN + f"Processing {len(all_news)} articles for virality...")
        self._processed_news = self._evaluate_news_virality_parallel(all_news)
        self._news_index = 0
        self._save_viral_news()

        # Report statistics
        print(Fore.GREEN + f"\nProceso completado:")
        print(f"- Fuentes exitosas: {successful_sources}/{total_sources}")
        print(f"- Artículos procesados: {len(all_news)}")
        print(f"- Artículos virales encontrados: {len(self._processed_news)}")

    def get_next_viral_news(self) -> Optional[Dict[str, Any]]:
        """
        Returns the next processed viral news article, or None if none left.
        """
        if self._news_index < len(self._processed_news):
            news = self._processed_news[self._news_index]
            self._news_index += 1
            return {
                'url': news['url'],
                'title': news.get('title', ''),
                'summary': news.get('summary', ''),
                'sentiment_polarity_textblob': news.get('sentiment_polarity_textblob', 0),
                'sentiment_compound_vader': news.get('sentiment_compound_vader', 0),
                'sentiment_compound_title': news.get('sentiment_compound_title', 0),
                'keyword_count': news.get('keyword_count', 0),
                'title_length': news.get('title_length', 0),
                'readability_score': news.get('readability_score', 0),
                'virality_score': news.get('virality_score', 0)
            }
        return None

    def _load_viral_news(self) -> None:
        """Loads viral news from file if it exists."""
        try:
            with open(self._viral_news_file, 'r', encoding='utf-8') as f:
                self._processed_news = json.load(f)
            print(Fore.GREEN + f"Loaded {len(self._processed_news)} viral news from {self._viral_news_file}.")
        except FileNotFoundError:
            print(Fore.YELLOW + f"File {self._viral_news_file} not found. No viral news loaded.")
        except json.JSONDecodeError:
            print(Fore.RED + f"Error decoding JSON from {self._viral_news_file}. No viral news loaded.")

    def _save_viral_news(self) -> None:
        """Saves processed viral news to file."""
        try:
            with open(self._viral_news_file, 'w', encoding='utf-8') as f:
                json.dump(self._processed_news, f, ensure_ascii=False, indent=4)
            print(Fore.MAGENTA + f"Stored {len(self._processed_news)} viral news in {self._viral_news_file}.")
        except Exception as e:
            print(Fore.RED + f"Error saving viral news to {self._viral_news_file}: {e}")

    def _fetch_rss_feed(self, url: str) -> Optional[bytes]:
        """Fetches RSS feed content from a URL."""
        headers = {'User-Agent': self._ua.random}
        try:
            response = requests.get(url, headers=headers, timeout=DEFAULT_RSS_TIMEOUT)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            print(Fore.RED + f"Error obtaining feed {url}: {e}")
            return None

    def _process_rss_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Processes a single RSS feed and returns recent news items."""
        try:
            print(Fore.CYAN + f"Processing feed: {feed_url}")
            content = self._fetch_rss_feed(feed_url)
            if not content:
                return []
            news_items = parse_rss_to_standard_object(content)
            return [
                {
                    'title': item.title,
                    'link': item.link,
                    'description': item.description,
                    'publishedAt': item.pub_date
                }
                for item in news_items
                if item.pub_date and self._is_recent(item.pub_date)
            ]
        except Exception as e:
            print(Fore.RED + f"Error processing RSS feed {feed_url}: {e}")
            return []

    def _process_newsapi(self) -> List[Dict[str, Any]]:
        """Fetches and filters recent news from NewsAPI."""
        try:
            newsapi_client = NewsAPIClient(self._config['newsapi_key'])
            print(Fore.CYAN + "Processing news from NewsAPI")
            newsapi_news = newsapi_client.get_latest_headlines(
                countries=DEFAULT_NEWSAPI_COUNTRIES,
                category='technology',
                page_size=20
            )
            return [
                news for news in newsapi_news
                if self._is_recent(news.get('publishedAt'))
            ]
        except Exception as e:
            print(Fore.RED + f"Error processing NewsAPI: {e}")
            return []

    def _process_currentsapi(self) -> List[Dict[str, Any]]:
        """Fetches and filters recent news from CurrentsAPI for multiple languages."""
        try:
            currents_client = CurrentsClient(self._config['currentsapi_key'])
            print(Fore.CYAN + "Processing news from CurrentsAPI")
            all_currents_news = []
            for language in DEFAULT_CURRENTS_LANGUAGES:
                try:
                    currents_news = currents_client.get_latest_headlines(
                        country='',
                        category='TECHNOLOGY',
                        language=language,
                        limit=20
                    )
                    recent_currents_news = [
                        news for news in currents_news
                        if self._is_recent(news.get('published_at'))
                    ]
                    all_currents_news.extend(recent_currents_news)
                except Exception as e:
                    print(Fore.YELLOW + f"Error fetching CurrentsAPI news for language {language}: {e}")
            return all_currents_news
        except Exception as e:
            print(Fore.RED + f"Error processing CurrentsAPI: {e}")
            return []

    def _evaluate_news_virality_parallel(self, all_news: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates virality of news articles in parallel."""
        results = []
        with ThreadPoolExecutor(max_workers=DEFAULT_MAX_WORKERS) as executor:
            future_to_news: Dict[Future, Dict[str, Any]] = {
                executor.submit(
                    self._evaluate_virality,
                    news.get('link') or news.get('url')
                ): news for news in all_news
            }
            for future in future_to_news:
                try:
                    result = future.result(timeout=60)
                    if result and result['virality_score'] > self._config.get('virality_threshold', DEFAULT_VIRALITY_THRESHOLD):
                        results.append(result)
                except Exception as e:
                    news = future_to_news[future]
                    url = news.get('link') or news.get('url')
                    print(Fore.RED + f"Error processing article {url}: {e}")
        return sorted(results, key=lambda news: news['virality_score'], reverse=True)

    def _is_recent(self, pub_date: Union[str, datetime, None]) -> bool:
        """Checks if a publication date is within the configured time window."""
        if not pub_date:
            return False
        parsed_date = self._parse_date(pub_date)
        if not parsed_date:
            return False
        now = datetime.now(parsed_date.tzinfo) if parsed_date.tzinfo else datetime.now()
        time_window = timedelta(days=self._config.get('time_window_days', DEFAULT_TIME_WINDOW_DAYS))
        return (now - parsed_date) <= time_window

    @staticmethod
    def _parse_date(pub_date: Union[str, datetime]) -> Optional[datetime]:
        """Parses a date string or returns datetime if already parsed."""
        if isinstance(pub_date, datetime):
            return pub_date
        try:
            return parser.parse(pub_date)
        except Exception:
            try:
                return datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
            except Exception:
                return None

    def _evaluate_virality(self, article_url: str) -> Optional[Dict[str, Any]]:
        """
        Evaluates the virality of a news article by analyzing its content.
        Returns a dictionary with analysis results or None if failed.
        """
        try:
            headers = {'User-Agent': self._ua.random}
            response = requests.get(article_url, headers=headers, timeout=DEFAULT_ARTICLE_TIMEOUT)
            response.raise_for_status()
            article = Article(article_url)
            article.download(input_html=response.text)
            article.parse()

            if not article.text:
                print(Fore.YELLOW + f"Could not extract text from {article_url}")
                return None

            title = article.title
            text = article.text

            sentiment_polarity_textblob = self._analyze_sentiment_textblob(text)
            sentiment_compound_vader = self._analyze_sentiment_vader(text)
            sentiment_compound_title = self._analyze_title_emotion(title)
            keyword_count = self._analyze_keywords(text, self._config['keywords']['es'])
            title_length = self._analyze_title_length(title)
            readability_score = self._analyze_readability(text)

            virality_score = (
                (sentiment_polarity_textblob * 0.1) +
                (sentiment_compound_vader * 0.1) +
                (sentiment_compound_title * 0.1) +
                (keyword_count / len(self._config['keywords']['es']) * 0.2) +
                (1 / (title_length + 1) * 0.1) +
                (1 / (readability_score + 1) * 0.1) +
                0.4
            )

            print(Fore.GREEN + f"News processed: {title} - Virality Score: {virality_score:.2f}")

            return {
                'url': article_url,
                'title': title,
                'summary': article.summary,
                'sentiment_polarity_textblob': sentiment_polarity_textblob,
                'sentiment_compound_vader': sentiment_compound_vader,
                'sentiment_compound_title': sentiment_compound_title,
                'keyword_count': keyword_count,
                'title_length': title_length,
                'readability_score': readability_score,
                'virality_score': virality_score
            }
        except Exception as e:
            print(Fore.RED + f"Error processing {article_url}: {e}")
            return None

    @staticmethod
    def _analyze_sentiment_textblob(text: str) -> float:
        """Analyzes sentiment polarity using TextBlob."""
        return TextBlob(text).sentiment.polarity

    def _analyze_sentiment_vader(self, text: str) -> float:
        """Analyzes sentiment using VADER."""
        sentiment = self._vader_analyzer.polarity_scores(text)
        return sentiment['compound']

    def _analyze_keywords(self, text: str, keywords: List[str]) -> int:
        """Counts the number of keywords present in the text."""
        doc = nlp(text)
        return sum(1 for token in doc if token.text.lower() in keywords)

    def _analyze_title_emotion(self, title: str) -> float:
        """Analyzes sentiment of the title using VADER."""
        sentiment = self._vader_analyzer.polarity_scores(title)
        return sentiment['compound']

    @staticmethod
    def _analyze_title_length(title: str) -> int:
        """Returns the number of words in the title."""
        return len(title.split())

    @staticmethod
    def _analyze_readability(text: str) -> float:
        """Analyzes readability using Flesch-Kincaid grade."""
        try:
            return textstat.flesch_kincaid_grade(text)
        except Exception as e:
            print(Fore.RED + f"Error analyzing readability: {e}")
            return 0.0

class CurrentsClient:
    """
    Client for interacting with the CurrentsAPI.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.latest_news_url = "https://api.currentsapi.services/v1/latest-news"
        self.search_url = "https://api.currentsapi.services/v1/search"
        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        """Initializes a requests session with retry logic."""
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def get_latest_headlines(
        self,
        country: str = '',
        category: Optional[str] = None,
        language: str = 'es',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetches the latest headlines from CurrentsAPI."""
        headers = {
            'Authorization': self.api_key,
            'User-Agent': UserAgent().random
        }
        params = {'country': country, 'language': language, 'limit': limit}
        if category:
            params['category'] = category

        try:
            print(Fore.CYAN + f"Fetching the latest headlines for country: {country}, category: {category}, language: {language}, limit: {limit}")
            response = self.session.get(
                self.latest_news_url,
                headers=headers,
                params=params,
                timeout=(5, 30)
            )
            response.raise_for_status()
            data = response.json()
            if 'news' in data:
                print(Fore.GREEN + f"Headlines fetched successfully. Got {len(data['news'])} articles.")
                return data['news']
            print(Fore.YELLOW + "No articles found in the response.")
            return []
        except requests.exceptions.Timeout as e:
            print(Fore.RED + f"Timeout error accessing CurrentsAPI: {e}")
            raise
        except requests.RequestException as e:
            print(Fore.RED + f"Error accessing CurrentsAPI: {e}")
            raise
        except json.JSONDecodeError as e:
            print(Fore.RED + f"Error decoding JSON response: {e}")
            return []
        except Exception as e:
            print(Fore.RED + f"Unexpected error in get_latest_headlines: {e}")
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=30))
    def search_news(
        self,
        query: str,
        language: str = 'es',
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Searches news articles in CurrentsAPI."""
        headers = {
            'Authorization': self.api_key,
            'User-Agent': UserAgent().random
        }
        params = {'keywords': query, 'language': language, 'limit': limit}
        if category:
            params['category'] = category
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        try:
            print(Fore.CYAN + f"Searching news for query: '{query}', language: {language}, limit: {limit}")
            response = self.session.get(
                self.search_url,
                headers=headers,
                params=params,
                timeout=(5, 30)
            )
            response.raise_for_status()
            data = response.json()
            if 'news' in data:
                print(Fore.GREEN + f"Search results fetched successfully. Got {len(data['news'])} articles.")
                return data['news']
            print(Fore.YELLOW + "No articles found for the given query.")
            return []
        except requests.exceptions.Timeout as e:
            print(Fore.RED + f"Timeout error in search_news: {e}")
            raise
        except requests.RequestException as e:
            print(Fore.RED + f"Error in search_news: {e}")
            raise
        except json.JSONDecodeError as e:
            print(Fore.RED + f"Error decoding JSON response in search_news: {e}")
            return []
        except Exception as e:
            print(Fore.RED + f"Unexpected error in search_news: {e}")
            return []

class NewsAPIClient:
    """
    Client for interacting with the NewsAPI.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = NewsApiClient(api_key=self.api_key)

    def get_latest_headlines(
        self,
        countries: List[str] = ['es'],
        category: Optional[str] = None,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetches the latest headlines from NewsAPI for multiple countries."""
        all_articles = []
        for country in countries:
            try:
                print(Fore.CYAN + f"Fetching the latest headlines for country: {country}, category: {category}, page_size: {page_size}")
                top_headlines = self.client.get_top_headlines(country=country, category=category, page_size=page_size)
                if top_headlines.get('status') == 'ok':
                    print(Fore.GREEN + "Headlines fetched successfully.")
                    all_articles.extend(top_headlines['articles'])
                else:
                    print(Fore.YELLOW + f"Error fetching headlines: {top_headlines.get('message', 'Unknown error')}")
            except Exception as e:
                print(Fore.RED + f"An error occurred: {e}")
        return all_articles

def main():
    """Main entry point for running the news processor."""
    # Load configuration from config.json
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(Fore.RED + f"Error loading configuration: {e}")
        return

    processor = NewsProcessor(config)

    # Retrieve viral news one by one
    while True:
        news = processor.get_next_viral_news()
        if not news:
            break
        print(f"Title: {news['title']}")
        print(f"Virality Score: {news['virality_score']:.2f}")
        print(f"URL: {news['url']}\n")

    # Process all news (should be run periodically, e.g., once a day)
    processor.process_all_news()

if __name__ == "__main__":
    main()