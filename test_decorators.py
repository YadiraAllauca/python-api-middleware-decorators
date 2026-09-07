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
    circuit_breaker,
    DecoratorError,
    RateLimitExceeded,
    CircuitBreakerOpen
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
    assert "Validation failed" in str(exc_info.value)


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
    assert "Circuit breaker is open" in str(exc_info.value)


def test_circuit_breaker_recovery():
    call_count = [0]
    
    @circuit_breaker(failure_threshold=2, recovery_timeout=0.3)
    def flaky_function():
        call_count[0] += 1
        if call_count[0] <= 2:
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
    assert call_count[0] == 3



def test_rate_limit_raises_typed_exception():
    @rate_limit(max_calls=1, period_seconds=1)
    def limited_function():
        return "success"

    limited_function()

    with pytest.raises(RateLimitExceeded):
        limited_function()


def test_rate_limit_state_is_isolated_per_decoration():
    @rate_limit(max_calls=1, period_seconds=1)
    def first_function():
        return "first"

    @rate_limit(max_calls=1, period_seconds=1)
    def second_function():
        return "second"

    first_function()

    with pytest.raises(RateLimitExceeded):
        first_function()

    assert second_function() == "second"


def test_rate_limit_same_function_decorated_twice_is_isolated():
    def endpoint():
        return "ok"

    limited_a = rate_limit(max_calls=1, period_seconds=1)(endpoint)
    limited_b = rate_limit(max_calls=1, period_seconds=1)(endpoint)

    limited_a()

    with pytest.raises(RateLimitExceeded):
        limited_a()

    assert limited_b() == "ok"


def test_circuit_breaker_raises_typed_exception():
    @circuit_breaker(failure_threshold=1, recovery_timeout=10)
    def failing_function():
        raise ConnectionError("Connection failed")

    with pytest.raises(ConnectionError):
        failing_function()

    with pytest.raises(CircuitBreakerOpen):
        failing_function()


def test_circuit_breaker_state_is_isolated_per_decoration():
    @circuit_breaker(failure_threshold=1, recovery_timeout=10)
    def failing_function():
        raise ConnectionError("Connection failed")

    @circuit_breaker(failure_threshold=1, recovery_timeout=10)
    def healthy_function():
        return "healthy"

    with pytest.raises(ConnectionError):
        failing_function()

    with pytest.raises(CircuitBreakerOpen):
        failing_function()

    assert healthy_function() == "healthy"


def test_circuit_breaker_half_open_counts_first_success():
    fail = [True]

    @circuit_breaker(failure_threshold=2, recovery_timeout=0.2)
    def flaky_function():
        if fail[0]:
            raise ConnectionError("Temporary failure")
        return "success"

    for _ in range(2):
        with pytest.raises(ConnectionError):
            flaky_function()

    with pytest.raises(CircuitBreakerOpen):
        flaky_function()

    time.sleep(0.25)
    fail[0] = False

    # Two successes must close the circuit: the first one happens on the same
    # call that transitions OPEN -> HALF_OPEN and has to be counted.
    assert flaky_function() == "success"
    assert flaky_function() == "success"

    # Circuit is CLOSED now, so a single failure must not reopen it.
    fail[0] = True
    with pytest.raises(ConnectionError):
        flaky_function()

    fail[0] = False
    assert flaky_function() == "success"


def test_retry_rejects_non_positive_max_attempts():
    with pytest.raises(ValueError):
        retry(max_attempts=0)

    with pytest.raises(ValueError):
        retry(max_attempts=-1)


def test_decorator_errors_share_a_common_base():
    assert issubclass(RateLimitExceeded, DecoratorError)
    assert issubclass(CircuitBreakerOpen, DecoratorError)


def test_decorator_error_catches_rate_limit_and_circuit_breaker():
    @rate_limit(max_calls=1, period_seconds=1)
    def limited_function():
        return "success"

    @circuit_breaker(failure_threshold=1, recovery_timeout=10)
    def failing_function():
        raise ConnectionError("Connection failed")

    limited_function()
    with pytest.raises(DecoratorError):
        limited_function()

    with pytest.raises(ConnectionError):
        failing_function()
    with pytest.raises(DecoratorError):
        failing_function()


def test_decorator_error_does_not_catch_wrapped_function_errors():
    @circuit_breaker(failure_threshold=5, recovery_timeout=10)
    def failing_function():
        raise ConnectionError("Connection failed")

    # The wrapped function's own error must propagate untouched, not as a
    # DecoratorError -- that is the whole point of the base class.
    with pytest.raises(ConnectionError):
        failing_function()
    assert not isinstance(ConnectionError("x"), DecoratorError)
