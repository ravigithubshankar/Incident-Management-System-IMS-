import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.models import RCA, RootCauseCategory


class TestMTTR:
    """Test MTTR (Mean Time To Repair) calculations"""
    
    def test_mttr_60_minutes(self):
        """Test MTTR calculation for exactly 60 minutes"""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 11, 0, 0)  # 1 hour later
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.mttr_minutes == 60.0
    
    def test_mttr_30_minutes(self):
        """Test MTTR calculation for 30 minutes"""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 30, 0)  # 30 minutes later
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.mttr_minutes == 30.0
    
    def test_mttr_90_minutes(self):
        """Test MTTR calculation for 90 minutes"""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 11, 30, 0)  # 1.5 hours later
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        assert rca.mttr_minutes == 90.0
    
    def test_mttr_with_seconds(self):
        """Test MTTR calculation with partial minutes"""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 45, 30)  # 45.5 minutes later
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        # Should be 45.5 minutes
        assert rca.mttr_minutes == 45.5
    
    def test_mttr_zero_raises(self):
        """Test MTTR calculation with zero duration raises ValueError"""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 0, 0)  # Same time
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            _ = rca.mttr_minutes
    
    def test_mttr_negative_raises(self):
        """Test MTTR calculation with negative duration raises ValueError"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)  # Later time
        end_time = datetime(2024, 1, 1, 10, 0, 0)   # Earlier time
        
        rca = RCA(
            id=uuid4(),
            incident_id=uuid4(),
            start_time=start_time,
            end_time=end_time,
            root_cause_category=RootCauseCategory.DB_FAILURE,
            fix_applied="x" * 50,
            prevention_steps="y" * 50,
            created_at=datetime.utcnow(),
            created_by="test_user"
        )
        
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            _ = rca.mttr_minutes
