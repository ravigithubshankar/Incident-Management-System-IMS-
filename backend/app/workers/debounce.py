import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog

from app.domain.models import Signal, WorkItem
from app.patterns.repository import WorkItemRepository
from app.db.redis_client import get_redis
from app.core.config import settings

logger = structlog.get_logger()

class DebounceEngine:
    """Debounce engine using Redis to prevent duplicate work items"""
    
    def __init__(self):
        self.redis_client = None
    
    async def get_redis(self):
        """Get Redis client (lazy initialization)"""
        if not self.redis_client:
            self.redis_client = await get_redis()
        return self.redis_client
    
    async def process(self, signal: Signal, work_item_repo: WorkItemRepository) -> WorkItem:
        """
        Process a signal through the debounce engine.
        Returns the associated WorkItem (new or existing).
        """
        redis_client = await self.get_redis()
        
        # Debounce key for this component
        debounce_key = f"ims:debounce:{signal.component_id}"
        
        # Increment counter and check if this is the first signal in window
        count = await redis_client.incr(debounce_key)
        
        if count == 1:
            # First signal - set expiration and create new work item
            await redis_client.expire(debounce_key, settings.debounce_window_seconds)
            
            logger.info(
                "Creating new work item",
                component_id=signal.component_id,
                severity=signal.severity.value
            )
            
            # Create new work item
            work_item = await work_item_repo.create(signal)
            
            # Link signal to work item
            signal.work_item_id = work_item.id
            
            return work_item
        else:
            # Additional signal - find existing open work item
            logger.info(
                "Linking signal to existing work item",
                component_id=signal.component_id,
                signal_count=count
            )
            
            # Find open work item for this component
            work_item = await work_item_repo.find_open(signal.component_id)
            
            if not work_item:
                # This shouldn't happen, but handle gracefully
                logger.warning(
                    "No open work item found for component",
                    component_id=signal.component_id
                )
                
                # Create new work item as fallback
                work_item = await work_item_repo.create(signal)
            
            # Link signal to work item
            signal.work_item_id = work_item.id
            
            return work_item
    
    async def reset_debounce(self, component_id: str) -> None:
        """Reset debounce counter for a component"""
        redis_client = await self.get_redis()
        debounce_key = f"ims:debounce:{component_id}"
        await redis_client.delete(debounce_key)
        
        logger.info(
            "Debounce reset",
            component_id=component_id
        )
    
    async def get_debounce_count(self, component_id: str) -> int:
        """Get current debounce count for a component"""
        redis_client = await self.get_redis()
        debounce_key = f"ims:debounce:{component_id}"
        
        try:
            count = await redis_client.get(debounce_key)
            return int(count) if count else 0
        except Exception:
            return 0
    
    async def cleanup_expired_keys(self) -> None:
        """Clean up expired debounce keys (Redis handles this automatically with TTL)"""
        # This is mainly for monitoring purposes
        redis_client = await self.get_redis()
        
        # Get all debounce keys
        keys = await redis_client.keys("ims:debounce:*")
        
        logger.info(
            "Debounce keys status",
            total_keys=len(keys)
        )
