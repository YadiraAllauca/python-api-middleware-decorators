# Python API Middleware Decorators

An educational demonstration of the **Decorator Pattern** in Python: how to wrap function behavior through composition so cross-cutting concerns can be added transparently. It implements a handful of decorators (timing, logging, retry, cache, rate limiting, validation, circuit breaker), a FastAPI example that uses them, and a test suite.

This is a teaching example, not a library you should install and put in front of traffic. See [Limitations](#limitations) for exactly where it stops.

## Overview

This project demonstrates the practical implementation of the Decorator Pattern through Python decorators. It shows how to add functionality (timing, logging, caching, retry logic, rate limiting, and validation) to existing functions without modifying their source code, following the **Open/Closed Principle** from SOLID principles.

## Pattern Explanation

The Decorator Pattern allows behavior to be added to individual objects dynamically, without affecting the behavior of other objects from the same class. In this implementation:

- **Base Functions**: Simple API views and business logic functions
- **Decorators**: Reusable wrappers that add cross-cutting concerns
- **Composition**: Multiple decorators can be stacked to combine behaviors
- **Parameterized Decorators**: Decorators that accept configuration parameters

## Features

### Basic Decorators

- **Timing Decorator**: Measures and logs execution time with error handling
- **Async Timing Decorator**: Measures execution time for async functions
- **Logging Decorator**: Logs function arguments and return values with exception tracking

### Advanced Decorators

- **Retry Decorator**: Automatically retries failed function calls with exponential backoff
- **Cache Decorator**: In-memory caching with configurable TTL (Time To Live)
- **Rate Limit Decorator**: Prevents function calls from exceeding a specified rate
- **Validation Decorator**: Validates function arguments before execution
- **Circuit Breaker**: Implements circuit breaker pattern to prevent cascading failures

### Additional Features

- **Error Handling**: Every decorator propagates exceptions instead of swallowing them
- **Typed Exceptions**: `RateLimitExceeded` and `CircuitBreakerOpen` so callers can catch precisely
- **Type Hints**: Type annotations throughout
- **Documentation**: Google-style docstrings for all decorators
- **Logging**: Uses Python's `logging` module rather than `print`
- **FastAPI Integration**: API example showing the decorators in a web handler
- **Unit Tests**: Test suite with pytest (27 tests)
- **CI/CD**: GitHub Actions workflow for automated testing

## Limitations

These are deliberate. The goal here is a readable illustration of the pattern, and the
list below is the honest gap between that and something you would deploy:

- **Not thread-safe.** `cache`, `rate_limit` and `circuit_breaker` read and mutate their
  state without any locking. This is not hypothetical in `api_example.py`: FastAPI runs
  `def` (non-`async def`) endpoints in a thread pool, so `/users/{user_id}` and
  `/products/{product_id}` are already executing concurrently across worker threads.
  Under load you can get duplicate cache misses, a rate limiter that lets more calls
  through than `max_calls`, and lost circuit-breaker failure counts.
- **The cache is unbounded.** There is no maximum size and no eviction policy. Expired
  entries are only removed when that exact key is requested again, so a function called
  with many distinct arguments grows the cache forever.
- **Cache backend is not pluggable.** Results live in a plain dict in the decorator's
  closure. There is no interface to swap in Redis or Memcached.
- **State is per-process and per-decoration.** Each `@rate_limit`/`@circuit_breaker`
  application owns its own counters. Run two workers and each enforces its own budget,
  so a `max_calls=5` limit admits 10 calls across two processes.
- **Only `timing` has an async variant.** `retry`, `cache`, `rate_limit` and
  `circuit_breaker` are synchronous. Applying them to an `async def` function wraps the
  coroutine object, not its result — `@cache` on an `async def` will cache a coroutine
  and hand back an already-awaited one on the next hit.
- **`cache` requires hashable-reprs, not hashable args.** The cache key is built with
  `str(args)`, so two different objects with the same `repr` collide, and objects with
  default `repr` (containing their `id`) never hit the cache.
- **No benchmarks.** Nothing here has been measured. Do not assume the caching or
  circuit-breaking overhead is negligible.

## Project Structure

```
python-api-middleware-decorators/
├── decorators.py              # All decorator implementations
├── api_example.py            # FastAPI example with decorators
├── test_decorators.py        # Unit tests
├── pytest.ini               # Pytest configuration
├── requirements.txt          # Project dependencies
├── .gitignore               # Git ignore rules
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI workflow
└── README.md                # This file
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from decorators import timing_decorator, logging_decorator

@timing_decorator
@logging_decorator
def get_user_data(user_id):
    return {"user_id": user_id, "name": f"Usuario {user_id}"}
```

### Running the Basic Example

```bash
python decorators.py
```

### Advanced Decorators

#### Retry Decorator

```python
from decorators import retry

@retry(max_attempts=3, delay=1, backoff=2, exceptions=(ConnectionError,))
def unreliable_service():
    # May raise ConnectionError
    return "success"
```

#### Cache Decorator

```python
from decorators import cache

@cache(ttl_seconds=60)
def expensive_operation(n):
    # Expensive computation
    return result
```

#### Rate Limit Decorator

```python
from decorators import rate_limit

@rate_limit(max_calls=5, period_seconds=60)
def api_endpoint():
    return {"data": "response"}
```

#### Validation Decorator

```python
from decorators import validate_input

@validate_input(user_id=lambda x: isinstance(x, int) and x > 0)
def get_user(user_id):
    return {"user_id": user_id}
```

#### Async Timing Decorator

```python
from decorators import async_timing_decorator
import asyncio

@async_timing_decorator
async def async_get_data():
    await asyncio.sleep(0.1)
    return {"data": "result"}
```

#### Circuit Breaker Decorator

```python
from decorators import circuit_breaker

@circuit_breaker(failure_threshold=5, recovery_timeout=60)
def external_api_call():
    # May raise ConnectionError
    return "response"
```

### FastAPI Example

Run the FastAPI server:

```bash
python api_example.py
```

Or with uvicorn:

```bash
uvicorn api_example:app --reload
```

The API will be available at `http://localhost:8000` with endpoints:

- `GET /users/{user_id}` - Cached user data with timing and logging
- `GET /products/{product_id}` - Rate-limited product endpoint (returns `429` once the budget is spent)
- `GET /orders/{order_id}` - Retry-enabled order endpoint
- `POST /process` - Input validation example

API documentation available at `http://localhost:8000/docs`

## Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=decorators --cov-report=html
```

Run async tests:

```bash
pytest -v test_decorators.py::test_async_timing_decorator
```

The project includes 27 unit tests covering:
- All decorator functionalities
- Error handling scenarios
- Async function support
- Circuit breaker state transitions, including the HALF_OPEN probe
- State isolation between separate decorator applications
- Decorator composition

## Implementation Details

### Decorator Stacking Order

When decorators are applied in reverse order:

```python
@timing_decorator      # Outer decorator
@logging_decorator     # Inner decorator
@cache(ttl_seconds=30) # Innermost decorator
def get_user_data(user_id):
    ...
```

The execution flow is:
1. `timing_decorator` wrapper starts timing
2. `logging_decorator` wrapper logs arguments
3. `cache` decorator checks cache
4. Original function executes (if cache miss)
5. `cache` decorator stores result
6. `logging_decorator` wrapper logs result
7. `timing_decorator` wrapper calculates and prints elapsed time

### Error Handling

All decorators include proper error handling:

- **Timing Decorator**: Captures execution time even when exceptions occur
- **Logging Decorator**: Logs exceptions before re-raising them
- **Retry Decorator**: Only retries specified exception types; rejects `max_attempts < 1` at decoration time
- **Rate Limit Decorator**: Raises `RateLimitExceeded` when the budget is spent
- **Circuit Breaker**: Raises `CircuitBreakerOpen` while the circuit is open
- **Validation Decorator**: Raises `ValueError` with descriptive messages

Note that `retry(exceptions=(Exception,))` — the default — will happily retry a
`RateLimitExceeded` or `CircuitBreakerOpen`, defeating the decorator underneath it.
When stacking `@retry` over either, pass the specific exceptions you mean to recover
from.

### Key Design Principles

- **Single Responsibility**: Each decorator handles one concern
- **Open/Closed Principle**: Functions are open for extension (via decorators) but closed for modification
- **Composition over Inheritance**: Behavior is added through composition, not class hierarchies
- **Separation of Concerns**: Cross-cutting concerns are isolated in decorators

## Decorator Reference

### `@timing_decorator`

Measures function execution time. Prints time even if function raises an exception.

### `@logging_decorator`

Logs function arguments before execution and results after execution. Logs exceptions.

### `@retry(max_attempts=3, delay=1, backoff=2, exceptions=(Exception,))`

Retries function execution on failure.

- `max_attempts`: Maximum number of retry attempts
- `delay`: Initial delay between retries in seconds
- `backoff`: Multiplier for delay after each retry
- `exceptions`: Tuple of exception types to catch and retry

### `@cache(ttl_seconds=60)`

Caches function results in memory.

- `ttl_seconds`: Time to live for cached values

### `@rate_limit(max_calls=5, period_seconds=60)`

Limits function call frequency.

- `max_calls`: Maximum number of calls allowed
- `period_seconds`: Time window in seconds

Raises `RateLimitExceeded`. Each application of the decorator keeps its own call
history; two decorated functions never share a budget.

### `@validate_input(**validators)`

Validates function arguments before execution.

- `**validators`: Keyword arguments mapping parameter names to validation functions

### `@async_timing_decorator`

Measures async function execution time. Similar to `@timing_decorator` but for async functions.

### `@circuit_breaker(failure_threshold=5, recovery_timeout=60, exceptions=(Exception,))`

Implements circuit breaker pattern to prevent cascading failures.

- `failure_threshold`: Number of failures before opening the circuit
- `recovery_timeout`: Time in seconds before attempting to close the circuit
- `exceptions`: Tuple of exception types that count as failures

Raises `CircuitBreakerOpen` while the circuit is open. After `recovery_timeout` the
circuit moves to HALF_OPEN and needs `HALF_OPEN_SUCCESSES_TO_CLOSE` (2) consecutive
successes to close. Each application of the decorator keeps its own state.

## CI/CD

The project includes a GitHub Actions workflow that:

- Runs tests on Python 3.8, 3.9, 3.10, and 3.11
- Generates coverage reports
- Validates code quality

Workflow runs automatically on push and pull requests.

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## Purpose

This project is a worked example of:

- **The Decorator Pattern**: composition instead of inheritance to add behavior
- **Parameterized decorators**: the three-level `decorator factory -> decorator -> wrapper` shape, and where per-decoration state belongs (the closure, not a module global)
- **Common resilience patterns**: retry with backoff, TTL caching, rate limiting, circuit breaking — implemented plainly enough to read in one sitting
- **Stacking order**: what changes when you reorder decorators
- **Testing decorators**: including state isolation and circuit-breaker state transitions
- **Framework integration**: the same decorators applied to FastAPI handlers

This pattern is fundamental in frameworks like Flask, Django, and FastAPI, where decorators are used extensively for routing, authentication, caching, and other cross-cutting concerns.

If you need these behaviors in a real service, reach for a maintained library —
`tenacity` for retries, `cachetools` for caching, `limits` or `slowapi` for rate
limiting, `pybreaker` for circuit breaking — all of which handle the concerns listed
under [Limitations](#limitations).

## License

This project is provided as an educational example.
