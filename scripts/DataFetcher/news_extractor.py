from newspaper import Article
from newspaper.article import ArticleException

class ArticleData:
    def __init__(self, title, authors, text, images, publish_date):
        self.title = title
        self.authors = authors
        self.text = text
        self.images = images
        self.publish_date = publish_date
    
    def __str__(self):
        return f"Title: {self.title}\nAuthors: {', '.join(self.authors)}\nDate: {self.publish_date}\nText: {self.text[:500]}...\nImages: {self.images}"

class NewsExtractor:
    def __init__(self):
        pass

    def extract_article(self, url):
        try:
            print(f"Extracting article from: {url}")
            article = Article(url)
            article.download()
            article.parse()
            
            return ArticleData(
                title=article.title,
                authors=article.authors,
                text=article.text,
                images=list(article.images),
                publish_date=article.publish_date
            )
        except ArticleException as e:
            print(f"Error extracting article: {e}")
            return None
