import time
import functools
import logging
import asyncio
from collections import defaultdict
from typing import Callable, Any, Dict, List, Tuple, Type, Union
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


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
            logger.info(f"Tiempo de ejecución de {func.__name__}: {execution_time:.4f} segundos")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"Error en {func.__name__} después de {execution_time:.4f} segundos: {e}")
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
            logger.info(f"Tiempo de ejecución de {func.__name__}: {execution_time:.4f} segundos")
            return result
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"Error en {func.__name__} después de {execution_time:.4f} segundos: {e}")
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
        logger.info(f"Llamando a {func.__name__} con argumentos: args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Resultado de {func.__name__}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error en {func.__name__}: {e}")
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
    """
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
                        logger.warning(f"Intento {attempt} fallido para {func.__name__}. Reintentando en {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Todos los intentos fallaron para {func.__name__}")
            
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
                    logger.debug(f"Cache hit para {func.__name__}")
                    return cache_store[cache_key]
                else:
                    del cache_store[cache_key]
                    del cache_timestamps[cache_key]
            
            result = func(*args, **kwargs)
            cache_store[cache_key] = result
            cache_timestamps[cache_key] = current_time
            logger.debug(f"Cache miss para {func.__name__}, resultado almacenado")
            return result
        return wrapper
    return decorator


_rate_limit_storage: Dict[int, List[float]] = defaultdict(list)


def rate_limit(max_calls: int = 5, period_seconds: int = 60) -> Callable:
    """Decorator that limits function call frequency.
    
    Args:
        max_calls: Maximum number of calls allowed.
        period_seconds: Time window in seconds.
        
    Returns:
        Decorator function.
        
    Example:
        >>> @rate_limit(max_calls=5, period_seconds=60)
        ... def api_endpoint():
        ...     return {"data": "response"}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_id = id(func)
            current_time = time.time()
            
            call_history = _rate_limit_storage[func_id]
            call_history[:] = [t for t in call_history if current_time - t < period_seconds]
            
            if len(call_history) >= max_calls:
                wait_time = period_seconds - (current_time - call_history[0])
                error_msg = f"Rate limit excedido para {func.__name__}. Espera {wait_time:.2f} segundos"
                logger.warning(error_msg)
                raise Exception(error_msg)
            
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
            func_sig = functools.signature(func)
            bound_args = func_sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, validator_func in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator_func(value):
                        error_msg = f"Validación fallida para parámetro '{param_name}' con valor: {value}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


_circuit_breaker_storage: Dict[int, Dict[str, Any]] = defaultdict(dict)


def circuit_breaker(failure_threshold: int = 5, recovery_timeout: int = 60, 
                     exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """Decorator that implements circuit breaker pattern to prevent cascading failures.
    
    Args:
        failure_threshold: Number of failures before opening the circuit.
        recovery_timeout: Time in seconds before attempting to close the circuit.
        exceptions: Tuple of exception types that count as failures.
        
    Returns:
        Decorator function.
        
    Example:
        >>> @circuit_breaker(failure_threshold=5, recovery_timeout=60)
        ... def external_service():
        ...     return "response"
    """
    def decorator(func: Callable) -> Callable:
        func_id = id(func)
        storage = _circuit_breaker_storage[func_id]
        storage.setdefault('state', CircuitState.CLOSED)
        storage.setdefault('failure_count', 0)
        storage.setdefault('last_failure_time', 0)
        storage.setdefault('success_count', 0)
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_time = time.time()
            state = storage['state']
            
            if state == CircuitState.OPEN:
                if current_time - storage['last_failure_time'] >= recovery_timeout:
                    storage['state'] = CircuitState.HALF_OPEN
                    storage['success_count'] = 0
                    logger.info(f"Circuit breaker para {func.__name__} en estado HALF_OPEN")
                else:
                    wait_time = recovery_timeout - (current_time - storage['last_failure_time'])
                    error_msg = f"Circuit breaker abierto para {func.__name__}. Espera {wait_time:.2f} segundos"
                    logger.warning(error_msg)
                    raise Exception(error_msg)
            
            try:
                result = func(*args, **kwargs)
                
                if state == CircuitState.HALF_OPEN:
                    storage['success_count'] += 1
                    if storage['success_count'] >= 2:
                        storage['state'] = CircuitState.CLOSED
                        storage['failure_count'] = 0
                        logger.info(f"Circuit breaker para {func.__name__} cerrado exitosamente")
                
                if state == CircuitState.CLOSED:
                    storage['failure_count'] = 0
                
                return result
                
            except exceptions as e:
                storage['failure_count'] += 1
                storage['last_failure_time'] = current_time
                
                if storage['failure_count'] >= failure_threshold:
                    storage['state'] = CircuitState.OPEN
                    logger.error(f"Circuit breaker abierto para {func.__name__} después de {failure_threshold} fallos")
                
                raise
        
        return wrapper
    return decorator


@timing_decorator
@logging_decorator
def get_user_data(user_id: int) -> Dict[str, Any]:
    time.sleep(0.1)
    return {"user_id": user_id, "name": f"Usuario {user_id}", "email": f"user{user_id}@example.com"}


@cache(ttl_seconds=30)
@timing_decorator
def expensive_operation(n: int) -> int:
    time.sleep(0.5)
    return sum(range(n))


@retry(max_attempts=3, delay=0.5)
@rate_limit(max_calls=3, period_seconds=10)
def unreliable_service() -> str:
    import random
    if random.random() < 0.7:
        raise ConnectionError("Error de conexión simulado")
    return "Servicio exitoso"


@validate_input(user_id=lambda x: isinstance(x, int) and x > 0)
def get_user_by_id(user_id: int) -> Dict[str, Any]:
    return {"user_id": user_id, "name": f"Usuario {user_id}"}


@async_timing_decorator
async def async_get_user_data(user_id: int) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"user_id": user_id, "name": f"Usuario {user_id}", "email": f"user{user_id}@example.com"}


@circuit_breaker(failure_threshold=3, recovery_timeout=10)
def external_api_call() -> str:
    import random
    if random.random() < 0.6:
        raise ConnectionError("API no disponible")
    return "API response"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=== Ejemplo básico ===")
    result = get_user_data(123)
    print(f"\nResultado final: {result}\n")
    
    print("=== Ejemplo con cache ===")
    print(expensive_operation(1000000))
    print(expensive_operation(1000000))
    print()
    
    print("=== Ejemplo con retry ===")
    for i in range(2):
        try:
            print(unreliable_service())
        except Exception as e:
            print(f"Error: {e}")
    print()
    
    print("=== Ejemplo con validación ===")
    try:
        print(get_user_by_id(456))
        print(get_user_by_id(-1))
    except ValueError as e:
        print(f"Error de validación: {e}")
    print()
    
    print("=== Ejemplo async ===")
    async def run_async_example():
        result = await async_get_user_data(789)
        print(f"Resultado async: {result}")
    asyncio.run(run_async_example())
    print()
    
    print("=== Ejemplo circuit breaker ===")
    for i in range(5):
        try:
            print(external_api_call())
        except Exception as e:
            print(f"Error: {e}")
