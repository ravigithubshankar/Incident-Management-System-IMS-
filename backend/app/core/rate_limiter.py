import asyncio
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()

class TokenBucket:
    """Thread-safe token bucket implementation"""
    
    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill_time = time.time()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens, return True if successful"""
        async with self.lock:
            now = time.time()
            time_passed = now - self.last_refill_time
            
            # Refill tokens based on time passed
            tokens_to_add = time_passed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill_time = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm"""
    
    def __init__(self, app, capacity: int = 10000, refill_rate: int = 10000):
        super().__init__(app)
        self.bucket = TokenBucket(capacity, refill_rate)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Try to consume a token
        if await self.bucket.consume():
            return await call_next(request)
        else:
            logger.warning("Rate limit exceeded", path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": "backpressure", "retry_after": 1},
                headers={"Retry-After": "1"}
            )
