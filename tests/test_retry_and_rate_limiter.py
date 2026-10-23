"""Fast deterministic retry/rate-limit edge cases without real sleeping."""
from unittest.mock import Mock
import pytest
from scripts.utils.rate_limiter import RateLimiter, NoopRateLimiter, create
from scripts.utils.retry import RetryError, is_transient_error, retry_with_backoff

@pytest.mark.parametrize("max_calls", [1, 2, 5])
def test_exact_token_budget_is_enforced(max_calls, monkeypatch):
    monkeypatch.setattr("scripts.utils.rate_limiter.time.time", lambda: 100.0)
    limiter = RateLimiter(max_calls=max_calls, period=60)
    assert [limiter.acquire(blocking=False) for _ in range(max_calls)] == [True] * max_calls
    assert limiter.acquire(blocking=False) is False

def test_tokens_refill_after_elapsed_time(monkeypatch):
    tick = [100.0]
    monkeypatch.setattr("scripts.utils.rate_limiter.time.time", lambda: tick[0])
    limiter = RateLimiter(2, period=10)
    assert limiter.acquire(False) is True
    assert limiter.acquire(False) is True
    assert limiter.acquire(False) is False
    tick[0] += 5
    assert limiter.acquire(False) is True
    assert limiter.acquire(False) is False

def test_refill_never_exceeds_capacity(monkeypatch):
    tick = [100.0]
    monkeypatch.setattr("scripts.utils.rate_limiter.time.time", lambda: tick[0])
    limiter = RateLimiter(3, period=10)
    tick[0] += 1000
    limiter.acquire(False)
    assert limiter.tokens == pytest.approx(2)

@pytest.mark.parametrize("max_calls", [None, 0, -7])
def test_rate_limit_factory_without_positive_quota_never_blocks(max_calls):
    limiter = create(max_calls)
    assert isinstance(limiter, NoopRateLimiter)
    assert all(limiter.acquire(False) for _ in range(100))

def test_rate_limit_factory_with_quota_is_real():
    assert isinstance(create(3, 10), RateLimiter)

@pytest.mark.parametrize("message", [
    "timeout", "Connection reset by peer", "429 rate limit", "service unavailable",
    "Bad Gateway", "internal error", "Gateway Timeout"
])
def test_known_transient_errors_are_classified(message):
    assert is_transient_error(RuntimeError(message))

@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_http_status_codes_are_detected(status):
    err = RuntimeError("unexpected")
    err.status_code = status
    assert is_transient_error(err)

@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_nonretryable_http_status_codes_remain_nontransient(status):
    err = RuntimeError("validation rejected")
    err.status_code = status
    assert not is_transient_error(err)

def test_retry_succeeds_on_second_attempt(monkeypatch):
    pauses = []
    monkeypatch.setattr("scripts.utils.retry.time.sleep", pauses.append)
    monkeypatch.setattr("scripts.utils.retry.random.uniform", lambda *a: 1.0)
    call_count = [0]
    @retry_with_backoff(retries=3, backoff_in_seconds=2)
    def sometimes():
        call_count[0] += 1
        if call_count[0] == 1:
            raise OSError("timeout")
        return "finished"
    assert sometimes() == "finished"
    assert call_count[0] == 2
    assert pauses == [2]

def test_retry_exhaustion_raises_with_attempt_count(monkeypatch):
    monkeypatch.setattr("scripts.utils.retry.time.sleep", lambda _: None)
    @retry_with_backoff(retries=3, backoff_in_seconds=0)
    def always_fails():
        raise RuntimeError("still down")
    with pytest.raises(RetryError, match="3 attempts"):
        always_fails()

def test_nontransient_error_is_not_retried(monkeypatch):
    pause = Mock()
    monkeypatch.setattr("scripts.utils.retry.time.sleep", pause)
    calls = []
    @retry_with_backoff(retries=3, should_retry=is_transient_error)
    def invalid():
        calls.append(1)
        raise ValueError("invalid credentials")
    with pytest.raises(ValueError, match="invalid credentials"):
        invalid()
    assert len(calls) == 1
    pause.assert_not_called()

def test_retry_backoff_capped(monkeypatch):
    sleeps = []
    monkeypatch.setattr("scripts.utils.retry.time.sleep", sleeps.append)
    monkeypatch.setattr("scripts.utils.retry.random.uniform", lambda *a: 1.0)
    @retry_with_backoff(retries=4, backoff_in_seconds=3, max_backoff_in_seconds=4)
    def unavailable():
        raise OSError("unavailable")
    with pytest.raises(RetryError):
        unavailable()
    assert sleeps == [3, 4, 4]

def test_success_never_sleeps(monkeypatch):
    pause = Mock()
    monkeypatch.setattr("scripts.utils.retry.time.sleep", pause)
    @retry_with_backoff(retries=3)
    def instant():
        return 42
    assert instant() == 42
    pause.assert_not_called()
