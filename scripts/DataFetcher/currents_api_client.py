import requests
from colorama import Fore, Style, init

# Inicializar Colorama
init(autoreset=True)

class CurrentsClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.latest_news_url = "https://api.currentsapi.services/v1/latest-news"
        self.search_url = "https://api.currentsapi.services/v1/search"
    
    def get_latest_headlines(self, country='es', category=None, language='es', limit=10):
        headers = {
            'Authorization': self.api_key
        }
        params = {
            'country': country,
            'language': language,
            'limit': limit
        }
        if category:
            params['category'] = category
        
        try:
            print(Fore.CYAN + f"Fetching the latest headlines for country: {country}, category: {category}, language: {language}, limit: {limit}")
            response = requests.get(self.latest_news_url, headers=headers, params=params)
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
    
    def search_news(self, query, language='es',category=None, start_date=None, end_date=None, limit=10):
        headers = {
            'Authorization': self.api_key
        }
        params = {
            'keywords': query,
            'language': language,
            'limit': limit,
            'category': category,
        }
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        try:
            print(Fore.CYAN + f"Searching news for query: '{query}', language: {language}, limit: {limit}")
            response = requests.get(self.search_url, headers=headers, params=params)
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
