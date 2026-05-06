import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Global variables
mongo_client = None
mongo_db = None

async def init_mongo():
    """Initialize MongoDB connection"""
    global mongo_client, mongo_db
    
    try:
        mongo_client = AsyncIOMotorClient(settings.mongo_uri)
        mongo_db = mongo_client.ims_signals
        
        # Test connection
        await mongo_db.command("ping")
        
        # Create indexes
        await create_indexes()
        
        logger.info("MongoDB initialized successfully")
        
    except Exception as e:
        logger.warning("MongoDB not available, running without database", error=str(e))
        # Don't raise the exception, allow application to start without MongoDB

async def create_indexes():
    """Create MongoDB indexes"""
    try:
        # Component and timestamp index for efficient queries
        await mongo_db.signals.create_index([
            ("component_id", 1),
            ("timestamp", -1)
        ])
        
        # Work item index for signal lookup
        await mongo_db.signals.create_index("work_item_id")
        
        # TTL index for automatic cleanup after 30 days
        await mongo_db.signals.create_index(
            "timestamp",
            expireAfterSeconds=30 * 24 * 60 * 60  # 30 days
        )
        
        logger.info("MongoDB indexes created successfully")
        
    except Exception as e:
        logger.error("Failed to create MongoDB indexes", error=str(e))
        raise

async def get_mongo_db():
    """Get MongoDB database instance"""
    if mongo_db is None:
        raise RuntimeError("MongoDB not initialized")
    return mongo_db

async def check_mongo() -> str:
    """Check MongoDB health"""
    try:
        if mongo_db is not None:
            await mongo_db.command("ping")
            return "ok"
        return "not_available"
    except Exception as e:
        logger.error("MongoDB health check failed", error=str(e))
        return "error"

async def close_mongo():
    """Close MongoDB connections"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connections closed")
