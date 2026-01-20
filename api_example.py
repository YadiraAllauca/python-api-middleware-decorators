from fastapi import FastAPI, HTTPException
from decorators import (
    timing_decorator,
    logging_decorator,
    cache,
    rate_limit,
    validate_input,
    retry
)
import time

app = FastAPI(title="API Example with Decorators")


@app.get("/")
def root():
    return {"message": "API Example with Decorator Pattern"}


@app.get("/users/{user_id}")
@timing_decorator
@logging_decorator
@cache(ttl_seconds=30)
def get_user(user_id: int):
    time.sleep(0.1)
    if user_id < 0:
        raise HTTPException(status_code=400, detail="user_id debe ser positivo")
    return {
        "user_id": user_id,
        "name": f"Usuario {user_id}",
        "email": f"user{user_id}@example.com"
    }


@app.get("/products/{product_id}")
@timing_decorator
@rate_limit(max_calls=5, period_seconds=60)
def get_product(product_id: int):
    time.sleep(0.05)
    return {
        "product_id": product_id,
        "name": f"Producto {product_id}",
        "price": product_id * 10
    }


@app.get("/orders/{order_id}")
@retry(max_attempts=3, delay=0.5)
@timing_decorator
def get_order(order_id: int):
    import random
    if random.random() < 0.3:
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible")
    return {
        "order_id": order_id,
        "status": "completed",
        "total": order_id * 25.5
    }


@validate_input(user_id=lambda x: isinstance(x, int) and x > 0)
def process_user_data(user_id: int):
    return {"processed": True, "user_id": user_id}


@app.post("/process")
@timing_decorator
def process_data(user_id: int):
    try:
        return process_user_data(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

