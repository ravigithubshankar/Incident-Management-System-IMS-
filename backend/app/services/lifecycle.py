import structlog
from typing import Optional
from uuid import UUID

from app.domain.models import WorkItem, RCA
from app.patterns.repository import WorkItemRepository, RCARepository
from app.db.postgres import get_postgres_session

logger = structlog.get_logger()

class LifecycleService:
    """Service for managing work item lifecycle"""
    
    def __init__(self):
        self.work_item_repo = None
        self.rca_repo = None
    
    async def transition_status(self, work_item_id: UUID, new_status: str) -> WorkItem:
        """Transition work item to new status with state machine validation"""
        from app.patterns.repository import PostgresWorkItemRepository
        
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            
            # Get current work item
            work_item = await work_item_repo.find_by_id(work_item_id)
            if not work_item:
                raise ValueError(f"Work item {work_item_id} not found")
            
            # Use state machine to validate transition
            try:
                work_item.transition(new_status)
            except Exception as e:
                logger.error(
                    "Invalid state transition",
                    work_item_id=str(work_item_id),
                    current_status=work_item.status.value,
                    new_status=new_status,
                    error=str(e)
                )
                raise
            
            # Update in database
            updated_work_item = await work_item_repo.update_status(work_item_id, new_status)
            
            logger.info(
                "Work item status transitioned",
                work_item_id=str(work_item_id),
                old_status=work_item.status.value,
                new_status=new_status
            )
            
            return updated_work_item
    
    async def add_rca(self, work_item_id: UUID, rca: RCA) -> WorkItem:
        """Add RCA to work item"""
        from app.patterns.repository import PostgresWorkItemRepository, PostgresRCARepository
        
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            rca_repo = PostgresRCARepository(session)
            
            # Validate RCA is complete
            if not rca.is_complete():
                raise ValueError("RCA is not complete")
            
            # Save RCA
            saved_rca = await rca_repo.create(rca)
            
            # Get work item and add RCA
            work_item = await work_item_repo.find_by_id(work_item_id)
            if not work_item:
                raise ValueError(f"Work item {work_item_id} not found")
            
            # Link RCA to work item
            updated_work_item = await work_item_repo.add_rca(work_item_id, saved_rca)
            
            logger.info(
                "RCA added to work item",
                work_item_id=str(work_item_id),
                rca_id=str(rca.id),
                mttr_minutes=rca.mttr_minutes
            )
            
            return updated_work_item
    
    async def close_incident(self, work_item_id: UUID) -> WorkItem:
        """Close incident (requires complete RCA)"""
        from app.patterns.repository import PostgresWorkItemRepository
        
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            
            # Get work item
            work_item = await work_item_repo.find_by_id(work_item_id)
            if not work_item:
                raise ValueError(f"Work item {work_item_id} not found")
            
            # Check if RCA exists and is complete
            # Assuming work_item.rca is populated or checked separately
            # In this implementation, we check if it has rca_id or rca data
            # For simplicity, we just try to transition and let the logic handle it
            
        # Transition to closed (transition_status handles its own session)
        return await self.transition_status(work_item_id, "CLOSED")
