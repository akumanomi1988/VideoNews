from newsapi import NewsApiClient
from colorama import Fore, Style, init

# Inicializar Colorama
init(autoreset=True)

class NewsAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = NewsApiClient(api_key=self.api_key)
    
    def get_latest_headlines(self, country='us', category=None, page_size=10):
        try:
            print(Fore.CYAN + f"Fetching the latest headlines for country: {country}, category: {category}, page_size: {page_size}")
            top_headlines = self.client.get_top_headlines(country=country, category=category, page_size=page_size)
            print(Fore.GREEN + "Headlines fetched successfully.")
            return top_headlines['articles']
        except Exception as e:
            print(Fore.RED + f"An error occurred: {e}")
            return []

