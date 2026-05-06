import structlog
from typing import Optional

from app.domain.models import WorkItem
from app.patterns.strategy import get_strategy

logger = structlog.get_logger()

class AlertingService:
    """Service for handling incident alerting"""
    
    def __init__(self):
        self.strategies = {}
    
    async def send_alert(self, work_item: WorkItem) -> None:
        """Send alert for work item based on component type and severity"""
        try:
            # Get appropriate alert strategy
            strategy = get_strategy(
                work_item.component_type.value,
                work_item.severity.value
            )
            
            # Send alert using strategy
            await strategy.alert(work_item)
            
            logger.info(
                "Alert sent successfully",
                work_item_id=str(work_item.id),
                component_id=work_item.component_id,
                severity=work_item.severity.value,
                strategy_name=strategy.__class__.__name__
            )
            
        except Exception as e:
            logger.error(
                "Failed to send alert",
                work_item_id=str(work_item.id),
                component_id=work_item.component_id,
                error=str(e)
            )
            # Don't raise - alerting failure shouldn't break processing
    
    async def send_custom_alert(
        self, 
        work_item: WorkItem, 
        message: str, 
        channel: Optional[str] = None
    ) -> None:
        """Send custom alert message"""
        try:
            logger.info(
                "CUSTOM_ALERT",
                work_item_id=str(work_item.id),
                component_id=work_item.component_id,
                message=message,
                channel=channel
            )
            
            # In production, this would integrate with actual notification systems
            
        except Exception as e:
            logger.error(
                "Failed to send custom alert",
                work_item_id=str(work_item.id),
                error=str(e)
            )
