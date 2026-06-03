"""
Asynchronous retry decorator utility for handling Telegram API errors.

This module provides a decorator (`retry_on_telegram_error`) that can be
applied to asynchronous functions interacting with the Telegram Bot API.
It automatically retries the decorated function upon encountering specific
transient errors like `TimedOut` or `NetworkError`, using an exponential
backoff strategy.
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Awaitable, TypeVar

from telegram.error import BadRequest, Forbidden, NetworkError, TimedOut

# Create a logger instance for this module
logger = logging.getLogger(__name__)

# Define a generic type variable for the wrapped function's return type
R = TypeVar('R')

def retry_on_telegram_error(max_retries: int = 3, delay_seconds: float = 1.0) \
        -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
    """
    An async decorator to retry a function call on specific Telegram API errors.

    This decorator wraps an asynchronous function and retries its execution
    if `telegram.error.TimedOut` or `telegram.error.NetworkError` occurs.
    It uses an exponential backoff strategy for delays between retries.
    Non-retryable errors (`Forbidden`, `BadRequest`) and non-Telegram
    exceptions are raised immediately.

    Args:
        max_retries: Maximum number of retries before giving up.
        delay_seconds: Initial delay in seconds for the first retry. This delay
                       doubles with each subsequent retry (exponential backoff).

    Returns:
        A decorator function that, when applied to an async function, returns
        a new async function with retry capabilities.
    """
    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Awaitable[R]:
            last_exception: Optional[Exception] = None
            current_delay: float = delay_seconds

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (TimedOut, NetworkError) as e:
                    last_exception = e
                    logger.warning(
                        "Telegram API error (%s): '%s' on attempt %d/%d for function '%s'. Retrying in %.2fs...",
                        type(e).__name__, e, attempt + 1, max_retries, func.__name__, current_delay,
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= 2
                except (Forbidden, BadRequest) as e:
                    logger.error(
                        "Non-retryable Telegram API error (%s): '%s' for function '%s'.",
                        type(e).__name__, e, func.__name__,
                    )
                    raise
                except Exception as e:
                    logger.error("Non-Telegram error during %s: %s", func.__name__, e, exc_info=True)
                    raise 

            final_error_message = (
                f"All {max_retries} retries failed for {func.__name__}. "
                f"Last error: {type(last_exception).__name__} - {last_exception}"
            )
            logger.error(final_error_message, exc_info=last_exception)
            
            if last_exception:
                raise last_exception
            # This part should ideally not be reached if last_exception is always set upon failure.
            # However, as a fallback to ensure an exception is always raised after all retries fail.
            raise Exception(f"All retries failed for {func.__name__} without a specific last exception caught.")
        return wrapper
    return decorator

if __name__ == '__main__':
    # Example usage of the decorator (conceptual)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    @retry_on_telegram_error(max_retries=3, delay_seconds=1)
    async def mock_telegram_call(fail_count: int) -> str:
        """Mocks a Telegram API call that might fail."""
        # Access attempts via function attribute for persistence across calls in this example
        if not hasattr(mock_telegram_call, 'attempts'):
            mock_telegram_call.attempts = 0 # type: ignore[attr-defined]
        
        mock_telegram_call.attempts += 1 # type: ignore[attr-defined]
        current_attempt_val = mock_telegram_call.attempts # type: ignore[attr-defined]

        logger.info(f"Attempting mock_telegram_call (attempt {current_attempt_val})...")
        if current_attempt_val <= fail_count:
            if current_attempt_val % 2 == 0:
                 logger.warning(f"Simulating TimedOut on attempt {current_attempt_val}")
                 raise TimedOut("Simulated timeout error")
            else:
                 logger.warning(f"Simulating NetworkError on attempt {current_attempt_val}")
                 raise NetworkError("Simulated network error")
        logger.info("mock_telegram_call successful!")
        return "Success"

    async def main_test() -> None:
        logger.info("--- Test 1: Should succeed after 2 failures ---")
        mock_telegram_call.attempts = 0 # type: ignore[attr-defined]
        try:
            result: str = await mock_telegram_call(fail_count=2)
            logger.info(f"Test 1 Result: {result}")
        except Exception as e:
            logger.error(f"Test 1 failed: {type(e).__name__} - {e}", exc_info=True)

        logger.info("\n--- Test 2: Should fail after 3 retries (fail_count=3) ---")
        mock_telegram_call.attempts = 0 # type: ignore[attr-defined]
        try:
            result = await mock_telegram_call(fail_count=3) # Max retries is 3 (default), so this should exhaust them
            logger.info(f"Test 2 Result (should not be reached): {result}")
        except Exception as e:
            logger.info(f"Test 2 failed as expected: {type(e).__name__} - {e}")

        logger.info("\n--- Test 3: Should succeed on first attempt (fail_count=0) ---")
        mock_telegram_call.attempts = 0 # type: ignore[attr-defined]
        try:
            result = await mock_telegram_call(fail_count=0)
            logger.info(f"Test 3 Result: {result}")
        except Exception as e:
            logger.error(f"Test 3 failed: {type(e).__name__} - {e}", exc_info=True)

    if __name__ == '__main__': # Ensure this block is also guarded
        asyncio.run(main_test())
