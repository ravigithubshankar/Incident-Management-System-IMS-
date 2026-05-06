import asyncio
from typing import List
import structlog

from app.core.config import settings
from app.domain.models import Signal, WorkItem
from app.workers.debounce import DebounceEngine
from app.patterns.repository import PostgresWorkItemRepository, MongoSignalRepository
from app.db.postgres import get_postgres_session
from app.db.mongo import get_mongo_db
from app.db.redis_client import get_redis
from app.services.alerting import AlertingService
from app.services.metrics import increment_signal_count, get_queue_depth

logger = structlog.get_logger()

# Global in-memory queue
signal_queue = asyncio.Queue(maxsize=settings.queue_max_size)

class QueueWorker:
    """Worker that processes signals from the queue"""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.debounce_engine = DebounceEngine()
        self.alerting_service = AlertingService()
    
    async def process_batch(self, signals: List[Signal]) -> None:
        """Process a batch of signals"""
        if not signals:
            return
        
        logger.info(
            "Processing signal batch",
            worker_id=self.worker_id,
            batch_size=len(signals)
        )
        
        # Get database connections
        mongo_db = await get_mongo_db()
        redis_client = await get_redis()
        
        # Initialize repositories
        signal_repo = MongoSignalRepository(mongo_db)
        
        # Process each signal
        work_items_to_alert = []
        
        try:
            # Save all signals to MongoDB first
            signal_ids = await signal_repo.save_batch(signals)
            for i, signal_id in enumerate(signal_ids):
                signals[i].id = signal_id
            
            # Use a single session for the entire batch
            async with get_postgres_session() as postgres_session:
                work_item_repo = PostgresWorkItemRepository(postgres_session)
                
                # Process each signal through debounce engine
                for signal in signals:
                    work_item = await self.debounce_engine.process(signal, work_item_repo)
                    
                    # Link signal to work item
                    await signal_repo.link_to_work_item(signal.id, work_item.id)
                    
                    # Update work item signal count
                    updated_work_item = await work_item_repo.update_signal_count(
                        work_item.id, work_item.signal_count + 1
                    )
                    
                    # Add to alert list if this is a new work item
                    if work_item.signal_count == 1:
                        work_items_to_alert.append(updated_work_item)
                    
                    # Update Redis dashboard
                    await self._update_dashboard(redis_client, updated_work_item)
                    
                    # Increment metrics
                    await increment_signal_count()
            
            # Send alerts for new work items
            for work_item in work_items_to_alert:
                await self.alerting_service.send_alert(work_item)
                
                # Publish WebSocket update
                await self._publish_websocket_update(redis_client, work_item)
            
            logger.info(
                "Batch processed successfully",
                worker_id=self.worker_id,
                signals_processed=len(signals),
                new_incidents=len(work_items_to_alert)
            )
            
        except Exception as e:
            logger.error(
                "Error processing signal batch",
                worker_id=self.worker_id,
                error=str(e),
                batch_size=len(signals)
            )
            raise
    
    async def _update_dashboard(self, redis_client, work_item: WorkItem) -> None:
        """Update dashboard state in Redis"""
        import json
        from datetime import datetime
        
        dashboard_data = {
            "id": str(work_item.id),
            "component_id": work_item.component_id,
            "component_type": work_item.component_type.value,
            "severity": work_item.severity.value,
            "status": work_item.status.value,
            "title": work_item.title,
            "signal_count": work_item.signal_count,
            "created_at": work_item.created_at.isoformat(),
            "updated_at": work_item.updated_at.isoformat()
        }
        
        await redis_client.hset(
            "ims:dashboard:incidents",
            str(work_item.id),
            json.dumps(dashboard_data)
        )
    
    async def _publish_websocket_update(self, redis_client, work_item: WorkItem) -> None:
        """Publish WebSocket update for real-time dashboard"""
        import json
        
        update_data = {
            "type": "incident_update",
            "incident": {
                "id": str(work_item.id),
                "component_id": work_item.component_id,
                "severity": work_item.severity.value,
                "status": work_item.status.value,
                "signal_count": work_item.signal_count
            }
        }
        
        await redis_client.publish(
            "ims:dashboard:updates",
            json.dumps(update_data)
        )

async def drain_queue(worker_id: int) -> None:
    """Worker function that continuously drains the queue"""
    worker = QueueWorker(worker_id)
    
    while True:
        try:
            # Collect a batch of signals
            batch = []
            batch_size = min(settings.batch_size, 100)  # Limit batch size
            
            # Try to get signals for the batch
            for _ in range(batch_size):
                try:
                    signal = signal_queue.get_nowait()
                    batch.append(signal)
                except asyncio.QueueEmpty:
                    break
            
            # Process the batch if we have signals
            if batch:
                await worker.process_batch(batch)
            else:
                # No signals, wait a bit
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(
                "Queue worker error",
                worker_id=worker_id,
                error=str(e)
            )
            await asyncio.sleep(1)  # Back off on error

async def start_queue_workers() -> None:
    """Start the queue worker pool"""
    logger.info(f"Starting {settings.worker_count} queue workers")
    
    tasks = []
    for i in range(settings.worker_count):
        task = asyncio.create_task(drain_queue(i))
        tasks.append(task)
    
    # Store tasks for potential cleanup
    start_queue_workers.tasks = tasks
    
    logger.info("Queue workers started successfully")

async def stop_queue_workers() -> None:
    """Stop all queue workers"""
    if hasattr(start_queue_workers, 'tasks'):
        for task in start_queue_workers.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*start_queue_workers.tasks, return_exceptions=True)
        logger.info("Queue workers stopped")
