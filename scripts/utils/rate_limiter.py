"""Shared token-bucket rate limiter for all API rate limiting needs."""
import threading
import time
from typing import Optional


class RateLimiter:
    def __init__(self, max_calls: int, period: float = 60.0):
        if max_calls <= 0:
            max_calls = 1
        self.max_calls = max_calls
        self.period = period
        self.tokens = max_calls
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, blocking: bool = True) -> bool:
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.max_calls,
                    self.tokens + elapsed * (self.max_calls / self.period),
                )
                self.last_refill = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
                if not blocking:
                    return False
                wait = self.period / self.max_calls
            time.sleep(wait)


class NoopRateLimiter(RateLimiter):
    def acquire(self, blocking: bool = True) -> bool:
        return True


def create(
    max_calls: Optional[int] = None, period: float = 60.0
) -> RateLimiter:
    if max_calls is not None and max_calls > 0:
        return RateLimiter(max_calls, period)
    return NoopRateLimiter(1, period)
