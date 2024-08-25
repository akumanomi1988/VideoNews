from newsapi import NewsApiClient
class NewsAPIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = NewsApiClient(api_key=self.api_key)
    
    def get_latest_headlines(self, country='us', category=None, page_size=10):
        try:
            # Obtener los titulares de noticias más recientes
            top_headlines = self.client.get_top_headlines(country=country, category=category, page_size=page_size)
            return top_headlines['articles']
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

# Ejemplo de uso directo
if __name__ == "__main__":
    config_path = "config/config.ini"  # Ruta a tu archivo de configuración
    from configparser import ConfigParser
    
    config = ConfigParser()
    config.read(config_path)

    api_key = config.get('NewsAPI', 'api_key')

    news_client = NewsAPIClient(api_key)
    headlines = news_client.get_latest_headlines(country='us', page_size=5)
    
    for article in headlines:
        print(f"Title: {article['title']}")
        print(f"Description: {article['description']}")
        print(f"URL: {article['url']}")
        print("-" * 40)
