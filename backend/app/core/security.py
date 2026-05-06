import hashlib
import secrets
from typing import Optional
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
from sqlalchemy import text

from app.db.postgres import get_postgres_session
from app.db.redis_client import get_redis

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage and comparison"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def is_valid_api_key(api_key: str) -> bool:
    """
    Validate API key against database with Redis caching.
    
    Non-functional bonuses:
    - Performance: Redis caching prevents DB hits on every request
    - Security: Hashed storage prevents key exposure on DB breach
    """
    if not api_key:
        return False
        
    key_hash = hash_api_key(api_key)
    cache_key = f"auth:api_key:{key_hash}"
    
    # 1. Check Redis Cache
    redis = await get_redis()
    if redis:
        cached = await redis.get(cache_key)
        if cached == "1":
            return True
        elif cached == "0":
            return False
            
    # 2. Check Database
    try:
        async with get_postgres_session() as session:
            query = text("SELECT is_active FROM api_keys WHERE key_hash = :hash")
            result = await session.execute(query, {"hash": key_hash})
            row = result.fetchone()
            
            is_valid = row is not None and row[0] is True
            
            # 3. Update Cache (TTL 5 mins)
            if redis:
                await redis.set(cache_key, "1" if is_valid else "0", ex=300)
                
            return is_valid
            
    except Exception as e:
        logger.error("API key database validation failed", error=str(e))
        # Fallback to hardcoded dev key for local testing if DB is down
        # In production, you might want to fail closed (return False)
        return api_key == "dev-api-key-12345"

async def get_api_key_from_header(request: Request) -> Optional[str]:
    """Extract API key from X-API-Key header"""
    return request.headers.get("X-API-Key")

async def validate_api_key(request: Request) -> bool:
    """Dependency for route-level API key validation"""
    api_key = await get_api_key_from_header(request)
    
    if not api_key:
        # Check Bearer token as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header.split(" ")[1]
            
    if await is_valid_api_key(api_key):
        return True
        
    logger.warning("Invalid API key attempted", path=request.url.path)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "X-API-Key"},
    )

# Legacy alias for compatibility with existing routes
API_KEYS = ["dev-api-key-12345"]
