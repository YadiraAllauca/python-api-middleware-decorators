import time
import functools
import inspect
import logging
import asyncio
from typing import Callable, Any, Dict, List, Tuple, Type
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class DecoratorError(Exception):
    """Base class for errors raised by the decorators in this module.

    Catch this to handle any decorator-originated rejection without also
    catching errors raised by the wrapped function itself.
    """


class RateLimitExceeded(DecoratorError):
    """Raised when a rate-limited function exceeds its allowed call budget."""


class CircuitBreakerOpen(DecoratorError):
    """Raised when a call is rejected because the circuit breaker is open."""


def timing_decorator(func: Callable) -> Callable:
    """Decorator that measures and logs function execution time.
    
    Args:
        func: Function to be wrapped.
        
    Returns:
        Wrapped function that logs execution time.
        
    Example:
        >>> @timing_decorator
        ... def my_function():
        ...     time.sleep(0.1)
        ...     return "done"
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f}s: {e}")
            raise
    return wrapper


def async_timing_decorator(func: Callable) -> Callable:
    """Decorator that measures and logs async function execution time.
    
    Args:
        func: Async function to be wrapped.
        
    Returns:
        Wrapped async function that logs execution time.
        
    Example:
        >>> @async_timing_decorator
        ... async def my_async_function():
        ...     await asyncio.sleep(0.1)
        ...     return "done"
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f}s: {e}")
            raise
    return wrapper


def logging_decorator(func: Callable) -> Callable:
    """Decorator that logs function arguments and return values.
    
    Args:
        func: Function to be wrapped.
        
    Returns:
        Wrapped function that logs input/output.
        
    Example:
        >>> @logging_decorator
        ... def my_function(x, y):
        ...     return x + y
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.info(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} raised: {e}")
            raise
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1, backoff: float = 2, 
          exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """Decorator that retries function execution on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch and retry.
        
    Returns:
        Decorator function.
        
    Example:
        >>> @retry(max_attempts=3, delay=1, exceptions=(ConnectionError,))
        ... def unreliable_function():
        ...     raise ConnectionError("Connection failed")

    Raises:
        ValueError: If max_attempts is less than 1.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1, got: {max_attempts}")

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(f"Attempt {attempt} failed for {func.__name__}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def cache(ttl_seconds: int = 60) -> Callable:
    """Decorator that caches function results in memory with TTL.
    
    Args:
        ttl_seconds: Time to live for cached values in seconds.
        
    Returns:
        Decorator function.
        
    Example:
        >>> @cache(ttl_seconds=30)
        ... def expensive_operation(n):
        ...     return sum(range(n))
    """
    def decorator(func: Callable) -> Callable:
        cache_store: Dict[str, Any] = {}
        cache_timestamps: Dict[str, float] = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            if cache_key in cache_store:
                if current_time - cache_timestamps[cache_key] < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cache_store[cache_key]
                else:
                    del cache_store[cache_key]
                    del cache_timestamps[cache_key]
            
            result = func(*args, **kwargs)
            cache_store[cache_key] = result
            cache_timestamps[cache_key] = current_time
            logger.debug(f"Cache miss for {func.__name__}, result stored")
            return result
        return wrapper
    return decorator


def rate_limit(max_calls: int = 5, period_seconds: int = 60) -> Callable:
    """Decorator that limits function call frequency.
    
    Args:
        max_calls: Maximum number of calls allowed.
        period_seconds: Time window in seconds.
        
    Returns:
        Decorator function.
        
    Raises:
        RateLimitExceeded: At call time, when the budget for the current
            window is exhausted.
        
    Example:
        >>> @rate_limit(max_calls=5, period_seconds=60)
        ... def api_endpoint():
        ...     return {"data": "response"}
    """
    def decorator(func: Callable) -> Callable:
        call_history: List[float] = []
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_time = time.time()
            
            call_history[:] = [t for t in call_history if current_time - t < period_seconds]
            
            if len(call_history) >= max_calls:
                wait_time = period_seconds - (current_time - call_history[0])
                error_msg = f"Rate limit exceeded for {func.__name__}. Retry in {wait_time:.2f}s"
                logger.warning(error_msg)
                raise RateLimitExceeded(error_msg)
            
            call_history.append(current_time)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_input(**validators: Callable[[Any], bool]) -> Callable:
    """Decorator that validates function arguments before execution.
    
    Args:
        **validators: Keyword arguments mapping parameter names to validation functions.
        
    Returns:
        Decorator function.
        
    Example:
        >>> @validate_input(user_id=lambda x: isinstance(x, int) and x > 0)
        ... def get_user(user_id):
        ...     return {"id": user_id}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_sig = inspect.signature(func)
            bound_args = func_sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, validator_func in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator_func(value):
                        error_msg = f"Validation failed for parameter '{param_name}' with value: {value}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


HALF_OPEN_SUCCESSES_TO_CLOSE = 2


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60, 
                     exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """Decorator that implements circuit breaker pattern to prevent cascading failures.
    
    After recovery_timeout the circuit moves to HALF_OPEN and needs
    HALF_OPEN_SUCCESSES_TO_CLOSE consecutive successes to close again. Any
    failure while HALF_OPEN reopens it once failure_threshold is reached.
    
    Args:
        failure_threshold: Number of failures before opening the circuit.
        recovery_timeout: Time in seconds before attempting to close the circuit.
        exceptions: Tuple of exception types that count as failures.
        
    Returns:
        Decorator function.
        
    Raises:
        CircuitBreakerOpen: At call time, when the circuit is open and the
            recovery timeout has not elapsed yet.
        
    Example:
        >>> @circuit_breaker(failure_threshold=5, recovery_timeout=60)
        ... def external_service():
        ...     return "response"
    """
    def decorator(func: Callable) -> Callable:
        storage: Dict[str, Any] = {
            'state': CircuitState.CLOSED,
            'failure_count': 0,
            'last_failure_time': 0.0,
            'success_count': 0,
        }
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_time = time.time()
            
            if storage['state'] == CircuitState.OPEN:
                if current_time - storage['last_failure_time'] >= recovery_timeout:
                    storage['state'] = CircuitState.HALF_OPEN
                    storage['success_count'] = 0
                    logger.info(f"Circuit breaker for {func.__name__} is now HALF_OPEN")
                else:
                    wait_time = recovery_timeout - (current_time - storage['last_failure_time'])
                    error_msg = f"Circuit breaker is open for {func.__name__}. Retry in {wait_time:.2f}s"
                    logger.warning(error_msg)
                    raise CircuitBreakerOpen(error_msg)
            
            # Read the state after the possible OPEN -> HALF_OPEN transition, so
            # the success that triggers the transition is counted as a probe.
            state = storage['state']
            
            try:
                result = func(*args, **kwargs)
                
                if state == CircuitState.HALF_OPEN:
                    storage['success_count'] += 1
                    if storage['success_count'] >= HALF_OPEN_SUCCESSES_TO_CLOSE:
                        storage['state'] = CircuitState.CLOSED
                        storage['failure_count'] = 0
                        logger.info(f"Circuit breaker for {func.__name__} closed after successful probes")
                
                if state == CircuitState.CLOSED:
                    storage['failure_count'] = 0
                
                return result
                
            except exceptions as e:
                storage['failure_count'] += 1
                storage['last_failure_time'] = current_time
                
                if storage['failure_count'] >= failure_threshold:
                    storage['state'] = CircuitState.OPEN
                    logger.error(f"Circuit breaker opened for {func.__name__} after {failure_threshold} failures")
                
                raise
        
        return wrapper
    return decorator


@timing_decorator
@logging_decorator
def get_user_data(user_id: int) -> Dict[str, Any]:
    time.sleep(0.1)
    return {"user_id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}


@cache(ttl_seconds=30)
@timing_decorator
def expensive_operation(n: int) -> int:
    time.sleep(0.5)
    return sum(range(n))


@retry(max_attempts=3, delay=0.5, exceptions=(ConnectionError,))
@rate_limit(max_calls=3, period_seconds=10)
def unreliable_service() -> str:
    import random
    if random.random() < 0.7:
        raise ConnectionError("Simulated connection error")
    return "Service call succeeded"


@validate_input(user_id=lambda x: isinstance(x, int) and x > 0)
def get_user_by_id(user_id: int) -> Dict[str, Any]:
    return {"user_id": user_id, "name": f"User {user_id}"}


@async_timing_decorator
async def async_get_user_data(user_id: int) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"user_id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}


@circuit_breaker(failure_threshold=3, recovery_timeout=10)
def external_api_call() -> str:
    import random
    if random.random() < 0.6:
        raise ConnectionError("API unavailable")
    return "API response"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=== Basic example ===")
    result = get_user_data(123)
    print(f"\nFinal result: {result}\n")
    
    print("=== Cache example ===")
    print(expensive_operation(1000000))
    print(expensive_operation(1000000))
    print()
    
    print("=== Retry example ===")
    for i in range(2):
        try:
            print(unreliable_service())
        except Exception as e:
            print(f"Error: {e}")
    print()
    
    print("=== Validation example ===")
    try:
        print(get_user_by_id(456))
        print(get_user_by_id(-1))
    except ValueError as e:
        print(f"Validation error: {e}")
    print()
    
    print("=== Async example ===")
    async def run_async_example():
        result = await async_get_user_data(789)
        print(f"Async result: {result}")
    asyncio.run(run_async_example())
    print()
    
    print("=== Circuit breaker example ===")
    for i in range(5):
        try:
            print(external_api_call())
        except Exception as e:
            print(f"Error: {e}")
