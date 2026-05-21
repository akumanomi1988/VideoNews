import sqlite3
from contextlib import contextmanager

# Añadir al principio del código
DATABASE_NAME = 'processed_news.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def initialize_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_news (
                url TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT,
                sentiment_polarity_textblob REAL,
                sentiment_compound_vader REAL,
                sentiment_compound_title REAL,
                keyword_count INTEGER,
                title_length INTEGER,
                readability_score REAL,
                virality_score REAL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# Ejecutar al inicio
initialize_database()

def is_url_processed(url):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT url FROM processed_news WHERE url = ?', (url,))
        return cursor.fetchone() is not None

def save_processed_news(news_data):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO processed_news 
            (url, title, summary, sentiment_polarity_textblob, 
             sentiment_compound_vader, sentiment_compound_title, 
             keyword_count, title_length, readability_score, virality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            news_data['url'],
            news_data.get('title', ''),
            news_data.get('summary', ''),
            news_data.get('sentiment_polarity_textblob', 0),
            news_data.get('sentiment_compound_vader', 0),
            news_data.get('sentiment_compound_title', 0),
            news_data.get('keyword_count', 0),
            news_data.get('title_length', 0),
            news_data.get('readability_score', 0),
            news_data.get('virality_score', 0)
        ))
        conn.commit()