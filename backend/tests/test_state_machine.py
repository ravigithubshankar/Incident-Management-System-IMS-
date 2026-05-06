import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.models import WorkItem, WorkItemStatus, InvalidTransitionError, RCARequiredError
from app.patterns.state import OpenState, InvestigatingState, ResolvedState, ClosedState


class TestStateMachine:
    """Test work item state machine transitions"""
    
    def test_open_to_investigating(self):
        """Test valid transition from OPEN to INVESTIGATING"""
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.OPEN,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Should transition successfully
        work_item.transition("INVESTIGATING")
        assert work_item.status == WorkItemStatus.INVESTIGATING
        assert isinstance(work_item._state, InvestigatingState)
    
    def test_investigating_to_resolved(self):
        """Test valid transition from INVESTIGATING to RESOLVED"""
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.INVESTIGATING,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        work_item._state = InvestigatingState()
        
        # Should transition successfully
        work_item.transition("RESOLVED")
        assert work_item.status == WorkItemStatus.RESOLVED
        assert isinstance(work_item._state, ResolvedState)
    
    def test_illegal_open_to_closed(self):
        """Test illegal transition from OPEN to CLOSED should raise error"""
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.OPEN,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Should raise InvalidTransitionError
        with pytest.raises(InvalidTransitionError, match="Cannot go from OPEN to CLOSED"):
            work_item.transition("CLOSED")
    
    def test_illegal_resolved_to_open(self):
        """Test illegal transition from RESOLVED to OPEN should raise error"""
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.RESOLVED,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        work_item._state = ResolvedState()
        
        # Should raise InvalidTransitionError
        with pytest.raises(InvalidTransitionError, match="Cannot go from RESOLVED to OPEN"):
            work_item.transition("OPEN")
    
    def test_close_without_rca(self):
        """Test closing without RCA should raise RCARequiredError"""
        from app.domain.models import RCA, RootCauseCategory
        
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.RESOLVED,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            rca=None  # No RCA
        )
        work_item._state = ResolvedState()
        
        # Should raise RCARequiredError
        with pytest.raises(RCARequiredError, match="RCA must be complete and valid before closing"):
            work_item.transition("CLOSED")
    
    def test_close_with_incomplete_rca(self):
        """Test closing with incomplete RCA should raise RCARequiredError"""
        from app.domain.models import RCA, RootCauseCategory
        
        # Create incomplete RCA (short fix)
        incomplete_rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 0),
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="short",  # Less than 50 chars
            prevention_steps="x" * 50,  # Exactly 50 chars
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.RESOLVED,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            rca=incomplete_rca
        )
        work_item._state = ResolvedState()
        
        # Should raise RCARequiredError
        with pytest.raises(RCARequiredError, match="RCA must be complete and valid before closing"):
            work_item.transition("CLOSED")
    
    def test_close_with_complete_rca(self):
        """Test closing with complete RCA should succeed"""
        from app.domain.models import RCA, RootCauseCategory
        
        # Create complete RCA
        complete_rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 0),
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,  # Exactly 50 chars
            prevention_steps="y" * 50,  # Exactly 50 chars
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.RESOLVED,
            title="Test Incident",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            rca=complete_rca
        )
        work_item._state = ResolvedState()
        
        # Should transition successfully
        work_item.transition("CLOSED")
        assert work_item.status == WorkItemStatus.CLOSED
        assert isinstance(work_item._state, ClosedState)
        assert work_item.closed_at is not None
