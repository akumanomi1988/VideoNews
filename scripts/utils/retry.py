import time
import logging
from functools import wraps
from typing import Type, Tuple, Optional, Callable, Any
import random

logger = logging.getLogger(__name__)

class RetryError(Exception):
    """Exception raised when all retries have been exhausted"""
    pass

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: int = 1,
    max_backoff_in_seconds: int = 30,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    should_retry: Optional[Callable[[Exception], bool]] = None
):
    """
    Decorator for retrying operations with exponential backoff
    
    Args:
        retries: Maximum number of retries
        backoff_in_seconds: Initial backoff time
        max_backoff_in_seconds: Maximum backoff time between retries
        exceptions: Tuple of exceptions to catch
        should_retry: Optional function to determine if an error should trigger retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add jitter to prevent thundering herd
            jitter = lambda: random.uniform(0.8, 1.2)
            
            attempt = 0
            current_backoff = backoff_in_seconds

            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    
                    if attempt == retries:
                        raise RetryError(f"Failed after {retries} attempts. Last error: {str(e)}")
                    
                    if should_retry and not should_retry(e):
                        raise
                    
                    # Calculate next backoff with jitter
                    sleep_time = min(current_backoff * jitter(), max_backoff_in_seconds)
                    
                    logger.warning(
                        f"Attempt {attempt}/{retries} failed: {str(e)}. "
                        f"Retrying in {sleep_time:.1f}s..."
                    )
                    
                    time.sleep(sleep_time)
                    current_backoff *= 2  # Exponential backoff
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is likely transient and should be retried
    
    Args:
        error: The exception to check
    
    Returns:
        bool: True if the error is likely transient
    """
    # Common transient error messages
    transient_messages = [
        "connection reset",
        "timeout",
        "too many requests",
        "rate limit",
        "server error",
        "internal error",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "temporarily unavailable"
    ]
    
    error_str = str(error).lower()
    
    # Check for common HTTP status codes indicating transient failures
    if hasattr(error, 'status_code'):
        if error.status_code in {429, 500, 502, 503, 504}:
            return True
            
    # Check error message for transient indicators
    return any(msg in error_str for msg in transient_messages)