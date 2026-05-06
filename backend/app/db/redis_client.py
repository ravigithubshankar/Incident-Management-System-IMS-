import asyncio
import redis.asyncio as redis
from redis.asyncio import Redis
import structlog
from typing import Optional

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global variables
redis_client: Optional[Redis] = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        
        logger.info("Redis initialized successfully")
        
    except Exception as e:
        logger.warning("Redis not available, running without cache", error=str(e))
        redis_client = None  # Ensure redis_client is None when connection fails
        # Don't raise the exception, allow application to start without Redis

async def get_redis() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url("redis://localhost:6379")
    return redis_client

async def check_redis() -> str:
    """Check Redis health"""
    try:
        if redis_client:
            await redis_client.ping()
            return "ok"
        return "not_available"
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return "error"

async def close_redis():
    """Close Redis connections"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connections closed")
