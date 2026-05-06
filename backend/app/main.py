import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from app.api.routes import signals, incidents, rca
from app.core.config import settings
from app.core.rate_limiter import RateLimitMiddleware
from app.core.exceptions import global_exception_handler
from app.core.security import validate_api_key
from app.db.postgres import init_postgres
from app.db.mongo import init_mongo
from app.db.redis_client import init_redis
from app.workers.queue_worker import signal_queue, start_queue_workers
from app.services.metrics import metrics_reporter

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Incident Management System")
    
    # Initialize databases
    await init_postgres()
    await init_mongo()
    await init_redis()
    
    # Start background workers
    await start_queue_workers()
    
    # Start metrics reporter
    asyncio.create_task(metrics_reporter())
    
    logger.info("All services initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Incident Management System")

app = FastAPI(
    title="Incident Management System",
    description="Production-grade incident management with real-time processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Include routers
app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
app.include_router(incidents.router, prefix="/api/v1", tags=["incidents"])
app.include_router(rca.router, prefix="/api/v1", tags=["rca"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.db.postgres import check_postgres
    from app.db.mongo import check_mongo
    from app.db.redis_client import check_redis
    
    checks = {
        "postgres": await check_postgres(),
        "mongo": await check_mongo(),
        "redis": await check_redis(),
    }
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, **checks}

@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    from app.services.metrics import get_current_metrics
    
    metrics = await get_current_metrics()
    return metrics

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    
    try:
        # Check if Redis is available before using pub/sub
        from app.db.redis_client import redis_client
        
        if redis_client is None:
            # Redis not available, send periodic status updates instead
            logger.warning("Redis not available, WebSocket running without pub/sub")
            while True:
                await asyncio.sleep(5)  # Send status every 5 seconds
                await websocket.send_text('{"type": "status", "message": "Redis not available"}')
        else:
            # Redis available, use pub/sub
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("ims:dashboard:updates")
            
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    await websocket.send_text(message["data"].decode())
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
