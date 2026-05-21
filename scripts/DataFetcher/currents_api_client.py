import requests
from colorama import Fore, init
from typing import List, Dict, Any, Optional
from datetime import datetime
from .interfaces import NewsProvider

# Inicializar Colorama
init(autoreset=True)

class CurrentsAPIProvider(NewsProvider):
    """Implementación de NewsProvider para Currents API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.latest_news_url = "https://api.currentsapi.services/v1/latest-news"
        self.search_url = "https://api.currentsapi.services/v1/search"
        self.languages = ['es', 'en', 'fr', 'ru']  # Idiomas soportados por defecto
    
    def get_latest_news(self, 
                       category: Optional[str] = None,
                       language: Optional[str] = None,
                       limit: int = 20) -> List[Dict[str, Any]]:
        """Obtiene las últimas noticias de Currents API"""
        all_articles = []
        
        # Si no se especifica un idioma, buscamos en todos los idiomas soportados
        languages_to_search = [language] if language else self.languages
        
        for lang in languages_to_search:
            try:
                print(Fore.CYAN + f"Fetching news from Currents API: {lang}, {category}")
                
                headers = {'Authorization': self.api_key}
                params = {
                    'language': lang,
                    'limit': min(limit, 20)  # Currents tiene un límite de 20 por request
                }
                if category:
                    params['category'] = category
                
                response = requests.get(
                    self.latest_news_url,
                    headers=headers,
                    params=params,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                
                if 'news' in data:
                    all_articles.extend(self._standardize_articles(data['news']))
                else:
                    print(Fore.YELLOW + "No articles found.")
                    
            except requests.exceptions.RequestException as e:
                print(Fore.RED + f"Error accessing Currents API: {e}")
                continue
                
        return all_articles[:limit]
    
    def search_news(self,
                   query: str,
                   language: Optional[str] = None,
                   category: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """Busca noticias específicas en Currents API"""
        try:
            headers = {'Authorization': self.api_key}
            params = {
                'keywords': query,
                'language': language if language else 'es',
                'limit': min(limit, 20)
            }
            
            if category:
                params['category'] = category
            if start_date:
                params['start_date'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                params['end_date'] = end_date.strftime('%Y-%m-%d')
            
            print(Fore.CYAN + f"Searching news in Currents API: {query}")
            response = requests.get(
                self.search_url,
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if 'news' in data:
                return self._standardize_articles(data['news'])[:limit]
            else:
                print(Fore.YELLOW + "No articles found.")
                return []
                
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Error searching Currents API: {e}")
            return []
    
    def _standardize_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Estandariza el formato de los artículos"""
        return [{
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'description': article.get('description', ''),
            'publishedAt': article.get('published', ''),
            'source': article.get('source', 'Currents API'),
            'content': article.get('content', ''),
            'author': article.get('author', '')
        } for article in articles]
