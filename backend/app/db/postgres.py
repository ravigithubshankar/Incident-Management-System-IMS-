import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Global variables
engine = None
async_session_maker = None

async def init_postgres():
    """Initialize PostgreSQL connection"""
    global engine, async_session_maker
    
    try:
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
            pool_size=20,
            max_overflow=10,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Test connection
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
            
        logger.info("PostgreSQL initialized successfully")
        
    except Exception as e:
        logger.warning("PostgreSQL not available, running without database", error=str(e))
        # Don't raise the exception, allow application to start without PostgreSQL


@asynccontextmanager
async def get_postgres_session() -> AsyncSession:
    """Get PostgreSQL session as a context manager"""
    if not async_session_maker:
        raise RuntimeError("PostgreSQL not available - database not initialized")
    
    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close()

async def check_postgres() -> str:
    """Check PostgreSQL health"""
    if not async_session_maker:
        return "not_available"
    try:
        # Test connection
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.error("PostgreSQL health check failed", error=str(e))
        return "error"

async def close_postgres():
    """Close PostgreSQL connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("PostgreSQL connections closed")
