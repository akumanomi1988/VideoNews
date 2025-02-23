from datetime import datetime, timezone, timedelta
from dateutil import parser
import requests
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timedelta
from newspaper import Article
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spacy
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from newsapi import NewsApiClient
import textstat

# Initialize colorama
init(autoreset=True)

# Load spaCy model
try:
    nlp = spacy.load("es_core_news_sm")
except OSError:
    print(Fore.RED + "Modelo es_core_news_sm not found. Downloading...")
    import spacy.cli
    spacy.cli.download("es_core_news_sm")
    nlp = spacy.load("es_core_news_sm")

class NewsProcessor:
    def __init__(self, config, viral_news_file='viral_news.json'):
        self._config = config
        self._viral_news_file = viral_news_file
        self._processed_news = []
        self._news_index = 0
        self._ua =  UserAgent()
        self._vader_analyzer = SentimentIntensityAnalyzer()
        # Cargar noticias virales desde el archivo si existe
        self._load_viral_news()

    def process_all_news(self):
        """Procesa todas las noticias desde diferentes fuentes y las almacena internamente."""
        all_news = []

        # Procesar feeds RSS
        for feed in self._config['rss_feeds']:
            print(Fore.CYAN + f"Processing feed: {feed}")
            content = self._fetch_rss_feed(feed)
            if content:
                news_items = self._parse_rss_feed(content, feed)
                recent_news = [news for news in news_items if self._is_recent(news['pub_date'])]
                all_news.extend(recent_news)

        # Procesar NewsAPI
        newsapi_client = NewsAPIClient(self._config['newsapi_key'])
        print(Fore.CYAN + "Processing news from NewsAPI")
        countries = ['es', 'us', 'gb', 'fr', 'ru']
        newsapi_news = newsapi_client.get_latest_headlines(countries=countries, category=None, page_size=20)
        recent_newsapi_news = [news for news in newsapi_news if self._is_recent(news.get('publishedAt'))]
        all_news.extend(recent_newsapi_news)

        # Procesar CurrentsAPI
        currents_client = CurrentsClient(self._config['currentsapi_key'])
        print(Fore.CYAN + "Processing news from CurrentsAPI")
        languages = ['es', 'en', 'fr', 'ru']
        for language in languages:
            currents_news = currents_client.get_latest_headlines(country='', category=None, language=language, limit=20)
            recent_currents_news = [news for news in currents_news if self._is_recent(news.get('published_at'))]
            all_news.extend(recent_currents_news)

        # Evaluar viralidad en paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._evaluate_virality, news['link'] if 'link' in news else news['url']): news for news in all_news}
            results = []
            for future in futures:
                result = future.result()
                if result and result['virality_score'] > self._config['virality_threshold']:
                    results.append(result)

        # Ordenar resultados por puntuación de viralidad
        self._processed_news = sorted(results, key=lambda news: news['virality_score'], reverse=True)
        self._news_index = 0

        # Guardar las noticias procesadas en el archivo
        self._save_viral_news()

    def get_next_viral_news(self):
        """
        Devuelve la siguiente noticia viral procesada.
        Retorna None si no hay más noticias disponibles.
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

    def _load_viral_news(self):
        """Carga las noticias virales desde el archivo si existe."""
        try:
            with open(self._viral_news_file, 'r', encoding='utf-8') as f:
                self._processed_news = json.load(f)
            print(Fore.GREEN + f"Loaded {len(self._processed_news)} viral news from {self._viral_news_file}.")
        except FileNotFoundError:
            print(Fore.YELLOW + f"File {self._viral_news_file} not found. No viral news loaded.")
        except json.JSONDecodeError:
            print(Fore.RED + f"Error decoding JSON from {self._viral_news_file}. No viral news loaded.")

    def _save_viral_news(self):
        """Guarda las noticias virales procesadas en el archivo."""
        try:
            with open(self._viral_news_file, 'w', encoding='utf-8') as f:
                json.dump(self._processed_news, f, ensure_ascii=False, indent=4)
            print(Fore.MAGENTA + f"Stored {len(self._processed_news)} viral news in {self._viral_news_file}.")
        except Exception as e:
            print(Fore.RED + f"Error saving viral news to {self._viral_news_file}: {e}")

    def _fetch_rss_feed(self, url):
        headers = {'User-Agent': self._ua.random}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.content.decode('utf-8')
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Error obtaining feed {url}: {e}")
            return None

    def _parse_rss_feed(self, content, url):
        soup = BeautifulSoup(content, 'xml')
        items = soup.find_all('item')
        news_items = []
        for item in items:
            title = item.title.text if item.title else ""
            link = item.link.text if item.link else ""
            pub_date = item.pubDate.text if item.pubDate else None
            news_items.append({'title': title, 'link': link, 'pub_date': pub_date, 'source': url})
        return news_items

    
    def _is_recent(self, pub_date):
        if not pub_date:
            return False
        try:
            pub_date = parser.parse(pub_date)
        except ValueError:
            try:
                pub_date = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
            except ValueError:
                return False

        # Hacer que `now` sea aware con zona horaria UTC
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        return now - pub_date < timedelta(days=self._config['time_window_days'])
    def _evaluate_virality(self, article_url):
        try:
            headers = {'User-Agent': self._ua.random}
            response = requests.get(article_url, headers=headers, timeout=10)
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

    def _analyze_sentiment_textblob(self, text):
        blob = TextBlob(text)
        return blob.sentiment.polarity

    def _analyze_sentiment_vader(self, text):
        sentiment = self._vader_analyzer.polarity_scores(text)
        return sentiment['compound']

    def _analyze_keywords(self, text, keywords):
        doc = nlp(text)
        keyword_count = sum(1 for token in doc if token.text.lower() in keywords)
        return keyword_count

    def _analyze_title_emotion(self, title):
        sentiment = self._vader_analyzer.polarity_scores(title)
        return sentiment['compound']

    def _analyze_title_length(self, title):
        return len(title.split())

    def _analyze_readability(self, text):
        try:
            flesch_kincaid_grade = textstat.flesch_kincaid_grade(text)
            return flesch_kincaid_grade
        except Exception as e:
            print(Fore.RED + f"Error analyzing readability: {e}")
            return 0


class CurrentsClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.latest_news_url = "https://api.currentsapi.services/v1/latest-news"
        self.search_url = "https://api.currentsapi.services/v1/search"

    def get_latest_headlines(self, country='', category=None, language='es', limit=20):
        headers = {'Authorization': self.api_key}
        params = {'country': country, 'language': language, 'limit': limit}
        if category:
            params['category'] = category

        try:
            print(Fore.CYAN + f"Fetching the latest headlines for country: {country}, category: {category}, language: {language}, limit: {limit}")
            response = requests.get(self.latest_news_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if 'news' in data:
                print(Fore.GREEN + "Headlines fetched successfully.")
                return data['news']
            else:
                print(Fore.YELLOW + "No articles found.")
                return []
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"An error occurred: {e}")
            return []

    def search_news(self, query, language='es', category=None, start_date=None, end_date=None, limit=20):
        headers = {'Authorization': self.api_key}
        params = {'keywords': query, 'language': language, 'limit': limit, 'category': category}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        try:
            print(Fore.CYAN + f"Searching news for query: '{query}', language: {language}, limit: {limit}")
            response = requests.get(self.search_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if 'news' in data:
                print(Fore.GREEN + "Search results fetched successfully.")
                return data['news']
            else:
                print(Fore.YELLOW + "No articles found for the given query.")
                return []
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"An error occurred: {e}")
            return []


class NewsAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = NewsApiClient(api_key=self.api_key)

    def get_latest_headlines(self, countries=['es'], category=None, page_size=20):
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


if __name__ == "__main__":
    # Load configuration from config.json
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    processor = NewsProcessor(config)

    # Obtener noticias virales una por una sin necesidad de procesar todo nuevamente
    while True:
        news = processor.get_next_viral_news()
        if not news:
            break
        print(f"Title: {news['title']}")
        print(f"Virality Score: {news['virality_score']:.2f}")
        print(f"URL: {news['url']}\n")

    # Procesar todas las noticias (ejecutar una vez al día)
    processor.process_all_news()