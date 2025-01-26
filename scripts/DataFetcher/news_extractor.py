from newspaper import Article
from newspaper.article import ArticleException

class NewsExtractor:
    def __init__(self):
        pass

    def extract_article(self, url):
        try:
            # Extrae el artículo usando la biblioteca newspaper3k

            print(url)
            article = Article(url)
            article.download()  # Descargar el contenido
            article.parse()  # Parsear el contenido del artículo
            return article.text
        except ArticleException as e:
            print(f"Error extracting article: {e}")
            return None