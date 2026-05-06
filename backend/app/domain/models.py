from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4
import pydantic.v1 as pydantic

if TYPE_CHECKING:
    from app.patterns.state import WorkItemState

class ComponentType(str, Enum):
    RDBMS = "RDBMS"
    CACHE = "CACHE"
    API = "API"
    QUEUE = "QUEUE"
    MCP_HOST = "MCP_HOST"
    NOSQL = "NOSQL"

class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class WorkItemStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class RootCauseCategory(str, Enum):
    DB_FAILURE = "DB_FAILURE"
    NETWORK = "NETWORK"
    MISCONFIGURATION = "MISCONFIGURATION"
    CAPACITY = "CAPACITY"
    SOFTWARE_BUG = "SOFTWARE_BUG"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    HUMAN_ERROR = "HUMAN_ERROR"

@dataclass
class Signal:
    id: str
    component_id: str
    component_type: ComponentType
    severity: Severity
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    work_item_id: Optional[UUID] = None
    ingested_at: Optional[datetime] = None

@dataclass
class RCA:
    id: UUID
    incident_id: UUID
    start_time: datetime
    end_time: datetime
    root_cause_category: RootCauseCategory
    fix_applied: str
    prevention_steps: str
    created_at: datetime
    created_by: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": str(self.id),
            "incident_id": str(self.incident_id),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "root_cause_category": self.root_cause_category.value,
            "fix_applied": self.fix_applied,
            "prevention_steps": self.prevention_steps,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "mttr_minutes": self.mttr_minutes
        }

    def is_complete(self) -> bool:
        """Check if RCA is complete and valid"""
        return all([
            bool(self.root_cause_category),
            len(self.fix_applied.strip()) >= 50,
            len(self.prevention_steps.strip()) >= 50,
            self.end_time > self.start_time,
            bool(self.incident_id),
        ])

    @property
    def mttr_minutes(self) -> float:
        """Calculate Mean Time To Repair in minutes"""
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return (self.end_time - self.start_time).total_seconds() / 60

@dataclass
class WorkItem:
    id: UUID
    component_id: str
    component_type: ComponentType
    severity: Severity
    status: WorkItemStatus
    title: str
    signal_count: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    rca: Optional[RCA] = None
    _state: Optional['WorkItemState'] = None

    def __post_init__(self):
        if self._state is None:
            from app.patterns.state import OpenState, InvestigatingState, ResolvedState, ClosedState
            
            status_map = {
                WorkItemStatus.OPEN: OpenState,
                WorkItemStatus.INVESTIGATING: InvestigatingState,
                WorkItemStatus.RESOLVED: ResolvedState,
                WorkItemStatus.CLOSED: ClosedState
            }
            
            state_class = status_map.get(self.status, OpenState)
            self._state = state_class()

    def transition(self, new_status: str) -> None:
        """Transition to new status using state machine"""
        if self._state:
            self._state.transition(self, new_status)
            self.status = WorkItemStatus(new_status)
            self.updated_at = datetime.utcnow()
            if new_status == WorkItemStatus.CLOSED.value:
                self.closed_at = datetime.utcnow()

    def get_status(self) -> str:
        """Get current status from state"""
        if self._state:
            return self._state.get_status()
        return self.status.value

class RCARequiredError(Exception):
    """Raised when trying to close incident without complete RCA"""
    pass

class InvalidTransitionError(Exception):
    """Raised when invalid state transition is attempted"""
    pass
