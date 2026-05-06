import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

from app.domain.models import Signal, ComponentType, Severity
from app.workers.debounce import DebounceEngine
from app.patterns.repository import WorkItemRepository


class MockWorkItemRepository(WorkItemRepository):
    """Mock repository for testing debounce functionality"""
    
    def __init__(self):
        self.work_items = {}
        self.open_items = {}
    
    async def create(self, signal: Signal):
        """Create a new work item"""
        work_item_id = uuid4()
        work_item = {
            'id': work_item_id,
            'component_id': signal.component_id,
            'component_type': signal.component_type,
            'severity': signal.severity,
            'status': 'OPEN',
            'signal_count': 1
        }
        self.work_items[work_item_id] = work_item
        self.open_items[signal.component_id] = work_item
        
        # Return mock work item object
        from app.domain.models import WorkItem
        return WorkItem(
            id=work_item_id,
            component_id=signal.component_id,
            component_type=signal.component_type,
            severity=signal.severity,
            status='OPEN',
            title=f"{signal.severity.value} Issue: {signal.component_id}",
            signal_count=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def find_open(self, component_id: str):
        """Find open work item for component"""
        if component_id in self.open_items:
            item = self.open_items[component_id]
            from app.domain.models import WorkItem
            return WorkItem(
                id=item['id'],
                component_id=item['component_id'],
                component_type=item['component_type'],
                severity=item['severity'],
                status=item['status'],
                title=item['title'],
                signal_count=item['signal_count'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        return None
    
    async def find_by_id(self, id):
        pass
    
    async def update_status(self, id, status):
        pass
    
    async def list_active(self, page, limit):
        pass
    
    async def count_active(self):
        pass
    
    async def update_signal_count(self, id, count):
        pass
    
    async def add_rca(self, work_item_id, rca):
        pass


@pytest.fixture
async def mock_redis():
    """Mock Redis for testing"""
    import fakeredis
    
    # Create fake Redis instance
    fake_redis = fakeredis.FakeStrictRedis()
    
    # Clear any existing data
    await fake_redis.flushall()
    
    return fake_redis


@pytest.fixture
def debounce_engine(mock_redis):
    """Create DebounceEngine with mock Redis"""
    engine = DebounceEngine()
    engine.redis_client = mock_redis
    return engine


class TestDebounce:
    """Test debounce engine functionality"""
    
    @pytest.mark.asyncio
    async def test_100_signals_one_work_item(self, debounce_engine, mock_redis):
        """Test that 100 signals for same component create exactly 1 work item"""
        repo = MockWorkItemRepository()
        component_id = "TEST_COMPONENT_001"
        
        # Create 100 signals for the same component
        signals = []
        for i in range(100):
            signal = Signal(
                id=str(uuid4()),
                component_id=component_id,
                component_type=ComponentType.RDBMS,
                severity=Severity.P0,
                message=f"Test signal {i}",
                timestamp=datetime.utcnow(),
                metadata={"index": i}
            )
            signals.append(signal)
        
        # Process all signals through debounce engine
        work_items = []
        for signal in signals:
            work_item = await debounce_engine.process(signal, repo)
            work_items.append(work_item)
        
        # Should have exactly 1 unique work item
        unique_work_item_ids = set(str(wi.id) for wi in work_items)
        assert len(unique_work_item_ids) == 1
        
        # All signals should be linked to the same work item
        for signal in signals:
            assert signal.work_item_id == work_items[0].id
    
    @pytest.mark.asyncio
    async def test_different_components_different_work_items(self, debounce_engine, mock_redis):
        """Test that signals for different components create different work items"""
        repo = MockWorkItemRepository()
        
        # Create signals for 3 different components
        component_ids = ["COMP_A", "COMP_B", "COMP_C"]
        signals = []
        
        for component_id in component_ids:
            for i in range(5):
                signal = Signal(
                    id=str(uuid4()),
                    component_id=component_id,
                    component_type=ComponentType.API,
                    severity=Severity.P1,
                    message=f"Test signal {i}",
                    timestamp=datetime.utcnow(),
                    metadata={"component": component_id}
                )
                signals.append(signal)
        
        # Process all signals
        work_items = []
        for signal in signals:
            work_item = await debounce_engine.process(signal, repo)
            work_items.append(work_item)
        
        # Should have 3 unique work items
        unique_work_item_ids = set(str(wi.id) for wi in work_items)
        assert len(unique_work_item_ids) == 3
        
        # Check that each component has its own work item
        component_work_items = {}
        for work_item in work_items:
            comp_id = work_item.component_id
            if comp_id not in component_work_items:
                component_work_items[comp_id] = work_item.id
        
        assert len(component_work_items) == 3
    
    @pytest.mark.asyncio
    async def test_new_burst_after_ttl(self, debounce_engine, mock_redis):
        """Test that new burst after TTL creates new work item"""
        repo = MockWorkItemRepository()
        component_id = "TEST_COMPONENT_TTL"
        
        # Create initial burst of signals
        initial_signals = []
        for i in range(10):
            signal = Signal(
                id=str(uuid4()),
                component_id=component_id,
                component_type=ComponentType.CACHE,
                severity=Severity.P2,
                message=f"Initial signal {i}",
                timestamp=datetime.utcnow(),
                metadata={"burst": "initial"}
            )
            initial_signals.append(signal)
        
        # Process initial signals
        initial_work_items = []
        for signal in initial_signals:
            work_item = await debounce_engine.process(signal, repo)
            initial_work_items.append(work_item)
        
        # Should have 1 work item from initial burst
        assert len(set(str(wi.id) for wi in initial_work_items)) == 1
        
        # Wait for debounce key to expire (TTL is 10 seconds)
        await asyncio.sleep(11)
        
        # Create new burst of signals for same component
        new_signals = []
        for i in range(5):
            signal = Signal(
                id=str(uuid4()),
                component_id=component_id,
                component_type=ComponentType.CACHE,
                severity=Severity.P2,
                message=f"New signal {i}",
                timestamp=datetime.utcnow(),
                metadata={"burst": "new"}
            )
            new_signals.append(signal)
        
        # Process new signals
        new_work_items = []
        for signal in new_signals:
            work_item = await debounce_engine.process(signal, repo)
            new_work_items.append(work_item)
        
        # Should have 2 total work items (1 from initial, 1 from new burst)
        all_work_items = initial_work_items + new_work_items
        unique_work_item_ids = set(str(wi.id) for wi in all_work_items)
        assert len(unique_work_item_ids) == 2
