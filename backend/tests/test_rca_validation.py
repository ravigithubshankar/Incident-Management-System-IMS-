import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.models import RCA, RootCauseCategory


class TestRCAValidation:
    """Test RCA validation and completeness checks"""
    
    def test_rca_incomplete_short_fix(self):
        """Test RCA with short fix applied should be incomplete"""
        rca = RCA(
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
        
        assert rca.is_complete() == False
    
    def test_rca_incomplete_short_prevention(self):
        """Test RCA with short prevention steps should be incomplete"""
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 0),
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,  # Exactly 50 chars
            prevention_steps="short",  # Less than 50 chars
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.is_complete() == False
    
    def test_rca_incomplete_missing_category(self):
        """Test RCA with missing root cause category should be incomplete"""
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 0),
            root_cause_category=None,  # Missing category
            fix_applied="x" * 50,
            prevention_steps="x" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.is_complete() == False
    
    def test_rca_complete(self):
        """Test complete RCA should pass validation"""
        rca = RCA(
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
        
        assert rca.is_complete() == True
    
    def test_rca_required_before_close(self):
        """Test that RCA must be complete before closing incident"""
        from app.domain.models import WorkItem, WorkItemStatus, RCARequiredError
        
        # Create work item without RCA
        work_item = WorkItem(
            id=uuid4(),
            component_id="TEST_COMPONENT",
            component_type="API",
            severity="P1",
            status=WorkItemStatus.RESOLVED,
            title="Test Incident",
            signal_count=5,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            rca=None
        )
        
        # Try to transition to CLOSED - should raise RCARequiredError
        with pytest.raises(RCARequiredError, match="RCA must be complete and valid before closing"):
            work_item.transition("CLOSED")
    
    def test_mttr_60_minutes(self):
        """Test MTTR calculation for 60 minutes"""
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 11, 0, 0),  # 1 hour later
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.mttr_minutes == 60.0
    
    def test_mttr_zero_raises(self):
        """Test MTTR calculation with zero duration raises error"""
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 0, 0),  # Same time
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            _ = rca.mttr_minutes
    
    def test_mttr_negative_raises(self):
        """Test MTTR calculation with negative duration raises error"""
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=datetime(2024, 1, 1, 12, 0, 0),  # Later time
            end_time=datetime(2024, 1, 1, 10, 0, 0),  # Earlier time
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            _ = rca.mttr_minutes
