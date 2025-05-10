from newsapi import NewsApiClient
from colorama import Fore, init
from typing import List, Dict, Any, Optional
from datetime import datetime
from .interfaces import NewsProvider

# Inicializar Colorama
init(autoreset=True)

class NewsAPIProvider(NewsProvider):
    """Implementación de NewsProvider para NewsAPI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = NewsApiClient(api_key=self.api_key)
        self.countries = ['es', 'us', 'gb', 'fr', 'ru']  # Países por defecto
    
    def get_latest_news(self, 
                       category: Optional[str] = None,
                       language: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene las últimas noticias de NewsAPI"""
        all_articles = []
        
        for country in self.countries:
            try:
                print(Fore.CYAN + f"Fetching news from NewsAPI: {country}, {category}")
                top_headlines = self.client.get_top_headlines(
                    country=country,
                    category=category,
                    page_size=min(limit, 100)  # NewsAPI tiene un límite de 100
                )
                
                if top_headlines.get('status') == 'ok':
                    all_articles.extend(self._standardize_articles(top_headlines['articles']))
                else:
                    print(Fore.YELLOW + f"Error: {top_headlines.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(Fore.RED + f"Error accessing NewsAPI: {e}")
                
        return all_articles[:limit]
    
    def search_news(self,
                   query: str,
                   language: Optional[str] = None,
                   category: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """Busca noticias específicas en NewsAPI"""
        try:
            params = {
                'q': query,
                'language': language,
                'sortBy': 'relevancy',
                'pageSize': min(limit, 100)
            }
            
            if start_date:
                params['from'] = start_date.isoformat()
            if end_date:
                params['to'] = end_date.isoformat()
                
            response = self.client.get_everything(**params)
            
            if response.get('status') == 'ok':
                return self._standardize_articles(response['articles'])[:limit]
            else:
                print(Fore.YELLOW + f"Error: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(Fore.RED + f"Error searching NewsAPI: {e}")
            return []
    
    def _standardize_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Estandariza el formato de los artículos"""
        return [{
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'description': article.get('description', ''),
            'publishedAt': article.get('publishedAt'),
            'source': article.get('source', {}).get('name', 'NewsAPI'),
            'content': article.get('content', ''),
            'author': article.get('author', '')
        } for article in articles]

