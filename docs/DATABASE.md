# Database Architecture

## Overview
The system uses SQLite databases for persistent storage, with separate databases handling different aspects of the application:
- `processed_news.db`: Stores processed articles and analytics
- `users.db`: Manages Telegram user information

## Schema Definitions

### Processed News Database
```sql
CREATE TABLE processed_news (
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
);
```

#### Fields Description
- `url`: Unique identifier for the news article
- `title`: Article headline
- `summary`: Generated summary of the article
- `sentiment_polarity_textblob`: TextBlob sentiment analysis score
- `sentiment_compound_vader`: VADER sentiment analysis score
- `sentiment_compound_title`: Title-specific sentiment score
- `keyword_count`: Number of identified keywords
- `title_length`: Character count of the title
- `readability_score`: Computed readability metric
- `virality_score`: Calculated viral potential
- `processed_at`: Timestamp of processing

### Users Database
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT
);
```

#### Fields Description
- `id`: Internal unique identifier
- `user_id`: Telegram user ID
- `username`: Telegram username
- `first_name`: User's first name
- `last_name`: User's last name

## Database Controllers

### ProcessedNewsController
- Manages article processing history
- Prevents duplicate processing
- Tracks content metrics
- Maintains processing analytics

#### Key Methods
```python
def is_url_processed(url: str) -> bool
def save_processed_news(news_data: dict) -> None
```

### UserController
- Handles Telegram user management
- Tracks user interactions
- Maintains user statistics

#### Key Methods
```python
def add_user(update: Update) -> None
def list_users() -> list
def get_user_count() -> int
```

## Data Flow

### News Processing Pipeline
1. URL submission
2. Duplicate check
3. Content processing
4. Metrics calculation
5. Database storage

### User Management Pipeline
1. User interaction
2. Profile validation
3. Database update
4. Statistics tracking

## Performance Considerations

### Optimizations
- Connection pooling via context managers
- Prepared statements for frequent queries
- Index optimization for URL lookups
- Atomic transactions for data integrity

### Best Practices
- Use context managers for connections
- Implement proper error handling
- Regular database maintenance
- Performance monitoring

## Example Usage

### Processing News
```python
from scripts.dbControllers.processed_news_controller import is_url_processed, save_processed_news

# Check if article was already processed
if not is_url_processed(article_url):
    # Process article
    news_data = process_article(article_url)
    # Save to database
    save_processed_news(news_data)
```

### Managing Users
```python
from scripts.dbControllers.user_controller import UserController

user_ctrl = UserController()

# Add new user
user_ctrl.add_user(telegram_update)

# Get user statistics
total_users = user_ctrl.get_user_count()
```

## Maintenance

### Database Backup
```bash
# Backup processed news database
sqlite3 processed_news.db ".backup 'backup_processed_news.db'"

# Backup users database
sqlite3 users.db ".backup 'backup_users.db'"
```

### Database Optimization
```sql
-- Analyze tables
ANALYZE processed_news;
ANALYZE users;

-- Rebuild indexes
REINDEX processed_news;
REINDEX users;
```

## Error Handling

### Common Issues
1. **Database Locked**
   - Use proper connection timeout
   - Implement retry logic
   - Check for long-running transactions

2. **Constraint Violations**
   - Validate data before insertion
   - Handle unique constraint violations
   - Implement proper error messages

3. **Connection Issues**
   - Implement connection pooling
   - Handle connection timeouts
   - Proper resource cleanup

### Error Recovery
```python
@contextmanager
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()
```