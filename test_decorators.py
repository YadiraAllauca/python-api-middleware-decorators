import pytest
import time
import asyncio
from decorators import (
    timing_decorator,
    async_timing_decorator,
    logging_decorator,
    retry,
    cache,
    rate_limit,
    validate_input,
    circuit_breaker
)


def test_timing_decorator():
    @timing_decorator
    def slow_function():
        time.sleep(0.1)
        return "done"
    
    result = slow_function()
    assert result == "done"


def test_timing_decorator_with_error():
    @timing_decorator
    def failing_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        failing_function()


def test_logging_decorator():
    @logging_decorator
    def test_function(x, y):
        return x + y
    
    result = test_function(2, 3)
    assert result == 5


def test_logging_decorator_with_error():
    @logging_decorator
    def failing_function():
        raise RuntimeError("Test error")
    
    with pytest.raises(RuntimeError):
        failing_function()


def test_retry_decorator_success():
    call_count = [0]
    
    @retry(max_attempts=3, delay=0.1)
    def flaky_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ConnectionError("Temporary error")
        return "success"
    
    result = flaky_function()
    assert result == "success"
    assert call_count[0] == 2


def test_retry_decorator_failure():
    @retry(max_attempts=3, delay=0.1)
    def always_failing():
        raise ValueError("Always fails")
    
    with pytest.raises(ValueError):
        always_failing()


def test_cache_decorator():
    call_count = [0]
    
    @cache(ttl_seconds=60)
    def cached_function(x):
        call_count[0] += 1
        return x * 2
    
    result1 = cached_function(5)
    result2 = cached_function(5)
    
    assert result1 == 10
    assert result2 == 10
    assert call_count[0] == 1


def test_cache_decorator_expiration():
    call_count = [0]
    
    @cache(ttl_seconds=0.1)
    def cached_function(x):
        call_count[0] += 1
        return x * 2
    
    cached_function(5)
    time.sleep(0.15)
    cached_function(5)
    
    assert call_count[0] == 2


def test_rate_limit_decorator():
    @rate_limit(max_calls=2, period_seconds=1)
    def limited_function():
        return "success"
    
    assert limited_function() == "success"
    assert limited_function() == "success"
    
    with pytest.raises(Exception) as exc_info:
        limited_function()
    assert "Rate limit" in str(exc_info.value)


def test_rate_limit_decorator_reset():
    @rate_limit(max_calls=1, period_seconds=0.1)
    def limited_function():
        return "success"
    
    limited_function()
    
    with pytest.raises(Exception):
        limited_function()
    
    time.sleep(0.15)
    assert limited_function() == "success"


def test_validate_input_decorator():
    @validate_input(x=lambda v: isinstance(v, int) and v > 0)
    def validated_function(x):
        return x * 2
    
    assert validated_function(5) == 10
    
    with pytest.raises(ValueError) as exc_info:
        validated_function(-1)
    assert "Validación fallida" in str(exc_info.value)


def test_validate_input_with_kwargs():
    @validate_input(user_id=lambda v: isinstance(v, int) and v > 0)
    def get_user(user_id):
        return {"id": user_id}
    
    assert get_user(user_id=123) == {"id": 123}
    
    with pytest.raises(ValueError):
        get_user(user_id=0)


def test_decorator_composition():
    call_count = [0]
    
    @timing_decorator
    @logging_decorator
    @cache(ttl_seconds=60)
    def composed_function(x):
        call_count[0] += 1
        return x * 3
    
    result1 = composed_function(4)
    result2 = composed_function(4)
    
    assert result1 == 12
    assert result2 == 12
    assert call_count[0] == 1


def test_retry_with_specific_exceptions():
    call_count = [0]
    
    @retry(max_attempts=3, delay=0.1, exceptions=(ConnectionError,))
    def specific_retry():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ConnectionError("Connection error")
        return "success"
    
    result = specific_retry()
    assert result == "success"


def test_retry_ignores_other_exceptions():
    @retry(max_attempts=3, delay=0.1, exceptions=(ConnectionError,))
    def raise_value_error():
        raise ValueError("Should not retry")
    
    with pytest.raises(ValueError):
        raise_value_error()


@pytest.mark.asyncio
async def test_async_timing_decorator():
    @async_timing_decorator
    async def async_function():
        await asyncio.sleep(0.1)
        return "done"
    
    result = await async_function()
    assert result == "done"


@pytest.mark.asyncio
async def test_async_timing_decorator_with_error():
    @async_timing_decorator
    async def failing_async_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        await failing_async_function()


def test_circuit_breaker_closed_state():
    call_count = [0]
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=1)
    def successful_function():
        call_count[0] += 1
        return "success"
    
    result = successful_function()
    assert result == "success"
    assert call_count[0] == 1


def test_circuit_breaker_opens_after_threshold():
    @circuit_breaker(failure_threshold=2, recovery_timeout=0.5)
    def failing_function():
        raise ConnectionError("Connection failed")
    
    with pytest.raises(ConnectionError):
        failing_function()
    
    with pytest.raises(ConnectionError):
        failing_function()
    
    with pytest.raises(Exception) as exc_info:
        failing_function()
    assert "Circuit breaker abierto" in str(exc_info.value)


def test_circuit_breaker_recovery():
    success_count = [0]
    
    @circuit_breaker(failure_threshold=2, recovery_timeout=0.3)
    def flaky_function():
        if success_count[0] < 3:
            success_count[0] += 1
            raise ConnectionError("Temporary failure")
        return "success"
    
    with pytest.raises(ConnectionError):
        flaky_function()
    
    with pytest.raises(ConnectionError):
        flaky_function()
    
    with pytest.raises(Exception):
        flaky_function()
    
    time.sleep(0.4)
    
    result = flaky_function()
    assert result == "success"

