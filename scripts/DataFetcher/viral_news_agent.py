import json
import logging
from typing import Dict, Any, List, Optional
from colorama import init, Fore
from fake_useragent import UserAgent
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spacy
from .news_api_client import NewsAPIProvider
from .currents_api_client import CurrentsAPIProvider
from .news_aggregator import NewsAggregator

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

PUB_DATE_FIELDS = ['pub_date', 'pubDate', 'published', 'updated', 'dc:date', 'lastBuildDate']

class NewsProcessor:
    """Procesa noticias de múltiples fuentes y evalúa su viralidad"""
    
    def __init__(self, config: Dict[str, Any], viral_news_file: str = 'viral_news.json'):
        self.config = config
        self.viral_news_file = viral_news_file
        self.logger = logging.getLogger(__name__)
        self._processed_news = []
        self._news_index = 0
        self._ua =  UserAgent()
        self._vader_analyzer = SentimentIntensityAnalyzer()
        
        # Inicializar proveedores de noticias
        self.providers = [
            NewsAPIProvider(config['newsapi_key']),
            CurrentsAPIProvider(config['currentsapi_key'])
        ]
        
        # Inicializar agregador
        self.aggregator = NewsAggregator(
            providers=self.providers,
            config=config,
            logger=self.logger
        )
        
        # Cargar noticias virales previas
        self._load_viral_news()

    def process_all_news(self) -> None:
        """Procesa todas las noticias desde diferentes fuentes y las almacena internamente."""
        try:
            print(Fore.CYAN + "Starting news processing...")
            
            # Obtener noticias virales
            viral_news = self.aggregator.get_viral_news(
                category='technology',
                limit=self.config.get('news_limit', 20),
                min_virality_score=self.config.get('virality_threshold', 0.5)
            )
            
            # Actualizar noticias procesadas
            self._processed_news = viral_news
            self._news_index = 0
            
            # Guardar resultados
            self._save_viral_news()
            
            print(Fore.GREEN + f"Processed {len(viral_news)} viral news articles")
            
        except Exception as e:
            print(Fore.RED + f"Error processing news: {e}")
            self.logger.exception("Error in process_all_news")

    def get_next_viral_news(self) -> Optional[Dict[str, Any]]:
        """
        Devuelve la siguiente noticia viral procesada.
        Retorna None si no hay más noticias disponibles.
        """
        if self._news_index < len(self._processed_news):
            news = self._processed_news[self._news_index]
            self._news_index += 1
            return news
        return None

    def _load_viral_news(self) -> None:
        """Carga las noticias virales desde el archivo si existe."""
        try:
            with open(self.viral_news_file, 'r', encoding='utf-8') as f:
                self._processed_news = json.load(f)
            print(Fore.GREEN + f"Loaded {len(self._processed_news)} viral news from {self.viral_news_file}")
        except FileNotFoundError:
            print(Fore.YELLOW + f"File {self.viral_news_file} not found. Starting fresh.")
        except json.JSONDecodeError:
            print(Fore.RED + f"Error decoding {self.viral_news_file}. Starting fresh.")
            self._processed_news = []

    def _save_viral_news(self) -> None:
        """Guarda las noticias virales procesadas en el archivo."""
        try:
            with open(self.viral_news_file, 'w', encoding='utf-8') as f:
                json.dump(self._processed_news, f, ensure_ascii=False, indent=4)
            print(Fore.GREEN + f"Saved {len(self._processed_news)} viral news to {self.viral_news_file}")
        except Exception as e:
            print(Fore.RED + f"Error saving viral news: {e}")
            self.logger.exception("Error saving viral news")


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