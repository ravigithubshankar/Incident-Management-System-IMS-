from abc import ABC, abstractmethod
from typing import Dict, Tuple
import structlog

from app.domain.models import WorkItem

logger = structlog.get_logger()

class AlertStrategy(ABC):
    """Abstract base class for alerting strategies"""
    
    @abstractmethod
    async def alert(self, incident: WorkItem) -> None:
        """Send alert for the given incident"""
        pass

class P0RDBMSStrategy(AlertStrategy):
    """P0 RDBMS failure alerting strategy"""
    
    async def alert(self, incident: WorkItem) -> None:
        logger.critical(
            "P0_ALERT",
            component=incident.component_id,
            incident_id=str(incident.id),
            severity=incident.severity.value
        )
        await self._slack_notify(
            f"🚨 P0 RDBMS FAILURE: {incident.component_id}",
            "#incidents-p0"
        )
    
    async def _slack_notify(self, message: str, channel: str) -> None:
        """Mock Slack notification - in production would call real Slack API"""
        logger.info("SLACK_NOTIFICATION", message=message, channel=channel)

class P1APIStrategy(AlertStrategy):
    """P1 API failure alerting strategy"""
    
    async def alert(self, incident: WorkItem) -> None:
        logger.error(
            "P1_ALERT",
            component=incident.component_id,
            incident_id=str(incident.id),
            severity=incident.severity.value
        )
        await self._slack_notify(
            f"🔴 P1 API FAILURE: {incident.component_id}",
            "#incidents-p1"
        )
    
    async def _slack_notify(self, message: str, channel: str) -> None:
        """Mock Slack notification - in production would call real Slack API"""
        logger.info("SLACK_NOTIFICATION", message=message, channel=channel)

class P2CacheStrategy(AlertStrategy):
    """P2 Cache issue alerting strategy"""
    
    async def alert(self, incident: WorkItem) -> None:
        logger.warning(
            "P2_ALERT",
            component=incident.component_id,
            incident_id=str(incident.id),
            severity=incident.severity.value
        )
        await self._slack_notify(
            f"🟡 P2 CACHE ISSUE: {incident.component_id}",
            "#incidents-p2"
        )
    
    async def _slack_notify(self, message: str, channel: str) -> None:
        """Mock Slack notification - in production would call real Slack API"""
        logger.info("SLACK_NOTIFICATION", message=message, channel=channel)

class P3QueueStrategy(AlertStrategy):
    """P3 Queue issue alerting strategy"""
    
    async def alert(self, incident: WorkItem) -> None:
        logger.info(
            "P3_ALERT",
            component=incident.component_id,
            incident_id=str(incident.id),
            severity=incident.severity.value
        )
        # No Slack notification for P3 issues

# Strategy registry — easily extensible
STRATEGY_MAP: Dict[Tuple[str, str], AlertStrategy] = {
    ("RDBMS",    "P0"): P0RDBMSStrategy(),
    ("API",      "P1"): P1APIStrategy(),
    ("CACHE",    "P2"): P2CacheStrategy(),
    ("QUEUE",    "P3"): P3QueueStrategy(),
    ("MCP_HOST", "P1"): P1APIStrategy(),
    ("NOSQL",    "P1"): P1APIStrategy(),
}

def get_strategy(component_type: str, severity: str) -> AlertStrategy:
    """Get alert strategy for component type and severity"""
    return STRATEGY_MAP.get((component_type, severity), P3QueueStrategy())
