from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models import WorkItem

from app.domain.models import RCARequiredError, InvalidTransitionError, WorkItemStatus

class WorkItemState(ABC):
    """Abstract base class for work item states"""
    
    @abstractmethod
    def transition(self, item: "WorkItem", new_status: str) -> None:
        """Transition to a new state"""
        pass
    
    @abstractmethod
    def get_status(self) -> str:
        """Get the current status string"""
        pass

class OpenState(WorkItemState):
    """State for newly created work items"""
    
    def transition(self, item: "WorkItem", new_status: str) -> None:
        if new_status == WorkItemStatus.INVESTIGATING.value:
            item._state = InvestigatingState()
        else:
            raise InvalidTransitionError(f"Cannot go from OPEN to {new_status}")
    
    def get_status(self) -> str:
        return WorkItemStatus.OPEN.value

class InvestigatingState(WorkItemState):
    """State for work items under investigation"""
    
    def transition(self, item: "WorkItem", new_status: str) -> None:
        if new_status == WorkItemStatus.RESOLVED.value:
            item._state = ResolvedState()
        else:
            raise InvalidTransitionError(f"Cannot go from INVESTIGATING to {new_status}")
    
    def get_status(self) -> str:
        return WorkItemStatus.INVESTIGATING.value

class ResolvedState(WorkItemState):
    """State for resolved work items"""
    
    def transition(self, item: "WorkItem", new_status: str) -> None:
        if new_status == WorkItemStatus.CLOSED.value:
            if not item.rca or not item.rca.is_complete():
                raise RCARequiredError("RCA must be complete and valid before closing")
            item._state = ClosedState()
            item.closed_at = datetime.utcnow()
        else:
            raise InvalidTransitionError(f"Cannot go from RESOLVED to {new_status}")
    
    def get_status(self) -> str:
        return WorkItemStatus.RESOLVED.value

class ClosedState(WorkItemState):
    """State for closed work items - terminal state"""
    
    def transition(self, item: "WorkItem", new_status: str) -> None:
        raise InvalidTransitionError("Cannot transition from CLOSED state")
    
    def get_status(self) -> str:
        return WorkItemStatus.CLOSED.value
