from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from colorama import Fore, init
from concurrent.futures import ThreadPoolExecutor
from newspaper import Article
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import spacy
import textstat

from .interfaces import NewsProvider
from .news_extractor import NewsExtractor, ArticleData

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

class NewsAggregator:
    """Clase que maneja la agregación y scoring de noticias de múltiples fuentes"""
    
    def __init__(self, 
                 providers: List[NewsProvider],
                 config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None):
        self.providers = providers
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.extractor = NewsExtractor()
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
    def get_viral_news(self,
                      category: Optional[str] = None,
                      language: Optional[str] = None,
                      limit: int = 20,
                      min_virality_score: float = 0.5) -> List[Dict[str, Any]]:
        """
        Obtiene noticias virales de todas las fuentes configuradas
        """
        all_news = []
        
        # Obtener noticias de todos los proveedores en paralelo
        with ThreadPoolExecutor(max_workers=len(self.providers)) as executor:
            future_to_provider = {
                executor.submit(
                    provider.get_latest_news,
                    category=category,
                    language=language,
                    limit=limit
                ): provider for provider in self.providers
            }
            
            for future in future_to_provider:
                try:
                    articles = future.result()
                    all_news.extend(articles)
                except Exception as e:
                    provider = future_to_provider[future]
                    self.logger.error(f"Error getting news from {provider.__class__.__name__}: {e}")
        
        # Filtrar por fecha
        recent_news = [
            news for news in all_news 
            if self._is_recent(news.get('publishedAt'))
        ]
        
        # Evaluar viralidad en paralelo
        viral_news = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(self._evaluate_virality, article['url']): article 
                for article in recent_news
            }
            
            for future in future_to_article:
                try:
                    result = future.result()
                    if result and result['virality_score'] >= min_virality_score:
                        viral_news.append(result)
                except Exception as e:
                    article = future_to_article[future]
                    self.logger.error(f"Error evaluating virality for {article['url']}: {e}")
        
        # Ordenar por puntuación de viralidad
        return sorted(
            viral_news,
            key=lambda x: x['virality_score'],
            reverse=True
        )[:limit]
    
    def _is_recent(self, pub_date) -> bool:
        """Verifica si una fecha de publicación está dentro de la ventana de tiempo configurada"""
        if not pub_date:
            return False
            
        try:
            if isinstance(pub_date, str):
                parsed_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            elif isinstance(pub_date, datetime):
                parsed_date = pub_date
            else:
                return False
                
            now = datetime.now(parsed_date.tzinfo)
            time_window = timedelta(days=self.config['time_window_days'])
            
            return (now - parsed_date) <= time_window
            
        except Exception as e:
            self.logger.error(f"Error parsing date {pub_date}: {e}")
            return False
    
    def _evaluate_virality(self, url: str) -> Optional[Dict[str, Any]]:
        """Evalúa la viralidad de un artículo"""
        try:
            # Extraer contenido del artículo
            article_data = self.extractor.extract_article(url)
            if not article_data:
                return None
                
            # Analizar texto
            text_metrics = self._analyze_text(article_data.text)
            title_metrics = self._analyze_title(article_data.title)
            
            # Calcular puntuación de viralidad
            virality_score = self._calculate_virality_score(text_metrics, title_metrics)
            
            return {
                'url': url,
                'title': article_data.title,
                'summary': article_data.text[:500],  # Primeros 500 caracteres como resumen
                'publishedAt': article_data.publish_date,
                'authors': article_data.authors,
                'images': article_data.images,
                **text_metrics,
                **title_metrics,
                'virality_score': virality_score
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating article {url}: {e}")
            return None
            
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Analiza el texto del artículo"""
        return {
            'sentiment_polarity_textblob': TextBlob(text).sentiment.polarity,
            'sentiment_compound_vader': self.vader_analyzer.polarity_scores(text)['compound'],
            'keyword_count': sum(1 for token in nlp(text) if token.text.lower() in self.config['keywords']['es']),
            'readability_score': textstat.flesch_kincaid_grade(text)
        }
        
    def _analyze_title(self, title: str) -> Dict[str, Any]:
        """Analiza el título del artículo"""
        return {
            'sentiment_compound_title': self.vader_analyzer.polarity_scores(title)['compound'],
            'title_length': len(title.split())
        }
        
    def _calculate_virality_score(self, text_metrics: Dict[str, Any], title_metrics: Dict[str, Any]) -> float:
        """Calcula la puntuación de viralidad basada en las métricas"""
        weights = self.config.get('virality_weights', {
            'sentiment_polarity_textblob': 0.1,
            'sentiment_compound_vader': 0.1,
            'sentiment_compound_title': 0.1,
            'keyword_count': 0.2,
            'title_length': 0.1,
            'readability_score': 0.1,
            'base_score': 0.3
        })
        
        score = weights['base_score']
        
        # Sentiment scores
        score += text_metrics['sentiment_polarity_textblob'] * weights['sentiment_polarity_textblob']
        score += text_metrics['sentiment_compound_vader'] * weights['sentiment_compound_vader']
        score += title_metrics['sentiment_compound_title'] * weights['sentiment_compound_title']
        
        # Keyword relevance
        max_keywords = len(self.config['keywords']['es'])
        score += (text_metrics['keyword_count'] / max_keywords) * weights['keyword_count']
        
        # Title optimization
        ideal_title_length = 10  # Título ideal de ~10 palabras
        title_score = 1 - abs(title_metrics['title_length'] - ideal_title_length) / ideal_title_length
        score += title_score * weights['title_length']
        
        # Readability (menor score es mejor)
        readability_score = 1 / (text_metrics['readability_score'] + 1)
        score += readability_score * weights['readability_score']
        
        return min(max(score, 0), 1)  # Normalizar entre 0 y 1