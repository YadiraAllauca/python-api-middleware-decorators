# Python API Middleware Decorators

A comprehensive demonstration of the **Decorator Pattern** in Python, showcasing how to dynamically wrap function behavior using composition to add cross-cutting concerns transparently. This project includes production-ready decorators with error handling, parameterized decorators, and a complete FastAPI example.

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

- **Error Handling**: All decorators include proper exception handling
- **Type Hints**: Complete type annotations for better code quality
- **Documentation**: Google-style docstrings for all decorators
- **Logging**: Professional logging using Python's logging module
- **FastAPI Integration**: Complete API example demonstrating real-world usage
- **Unit Tests**: Comprehensive test suite with pytest (20+ tests)
- **CI/CD**: GitHub Actions workflow for automated testing
- **Production Ready**: Follows SOLID principles and best practices

## Project Structure

```
python-api-middleware-decorators/
├── decorators.py              # All decorator implementations
├── api_example.py            # FastAPI example with decorators
├── test_decorators.py        # Comprehensive unit tests
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
- `GET /products/{product_id}` - Rate-limited product endpoint
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

The project includes 20+ unit tests covering:
- All decorator functionalities
- Error handling scenarios
- Async function support
- Circuit breaker state transitions
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
- **Retry Decorator**: Only retries specified exception types
- **Rate Limit Decorator**: Raises descriptive exceptions when limits are exceeded
- **Validation Decorator**: Raises `ValueError` with descriptive messages

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

This project demonstrates:

- **Pattern Mastery**: Deep understanding of the Decorator Pattern
- **Production Skills**: Error handling, testing, and real-world integration
- **Code Quality**: SOLID principles, type hints, docstrings, and best practices
- **Async Support**: Handling both sync and async functions
- **Advanced Patterns**: Circuit breaker implementation
- **Framework Integration**: Practical FastAPI example
- **Testing**: Comprehensive unit test coverage (20+ tests)
- **DevOps**: CI/CD pipeline with GitHub Actions

This pattern is fundamental in frameworks like Flask, Django, and FastAPI, where decorators are used extensively for routing, authentication, caching, and other cross-cutting concerns.

## License

This project is provided as an educational example.
