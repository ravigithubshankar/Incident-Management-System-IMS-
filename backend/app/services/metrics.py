import asyncio
import time
from typing import Dict, Any
import structlog

from app.workers.throughput import get_signal_rate, get_queue_depth, get_worker_utilisation
from app.patterns.repository import WorkItemRepository, PostgresWorkItemRepository
from app.db.postgres import get_postgres_session

logger = structlog.get_logger()

class MetricsService:
    """Service for collecting and reporting system metrics"""
    
    def __init__(self):
        self.last_report_time = time.time()
        self.signal_count = 0
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            # Get queue metrics
            signal_rate = await get_signal_rate()
            queue_depth = await get_queue_depth()
            worker_utilisation = await get_worker_utilisation()
            
            # Get active incidents count (skip if PostgreSQL not available)
            active_incidents = 0
            # Check if PostgreSQL is available by checking global variables
            from app.db.postgres import engine, async_session_maker
            if engine is not None and async_session_maker is not None:
                try:
                    session = await get_postgres_session()
                    try:
                        work_item_repo = PostgresWorkItemRepository(session)
                        active_incidents = await work_item_repo.count_active()
                    finally:
                        await session.close()
                except Exception:
                    # Any error during PostgreSQL operations, skip active incidents count
                    active_incidents = 0
            # else: PostgreSQL not available, active_incidents remains 0
            
            return {
                "signals_per_sec": signal_rate,
                "queue_depth": queue_depth,
                "active_incidents": active_incidents,
                "worker_utilisation": worker_utilisation,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error("Failed to get metrics", error=str(e))
            return {
                "signals_per_sec": 0.0,
                "queue_depth": 0,
                "active_incidents": 0,
                "worker_utilisation": "0/20",
                "timestamp": time.time(),
                "error": str(e)
            }

# Global metrics service instance
metrics_service = MetricsService()

async def get_current_metrics() -> Dict[str, Any]:
    """Get current system metrics (convenience function)"""
    return await metrics_service.get_current_metrics()

async def increment_signal_count():
    """Increment signal processing count"""
    metrics_service.signal_count += 1

async def metrics_reporter() -> None:
    """Background task that reports metrics every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            
            metrics = await get_current_metrics()
            
            logger.info(
                "THROUGHPUT_METRICS",
                **metrics
            )
            
            # Also print to console for visibility
            print(f"[METRICS] {metrics}")
            
        except Exception as e:
            logger.error("Metrics reporter error", error=str(e))
            await asyncio.sleep(5)
