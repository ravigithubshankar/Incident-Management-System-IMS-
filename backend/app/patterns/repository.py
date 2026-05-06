from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.domain.models import WorkItem, Signal, RCA, WorkItemStatus, ComponentType, Severity
from app.core.resilience import with_retry
from app.core.exceptions import DatabaseError

class WorkItemRepository(ABC):
    """Abstract repository for WorkItem operations"""
    
    @abstractmethod
    async def create(self, signal: Signal) -> WorkItem:
        """Create a new work item from a signal"""
        pass
    
    @abstractmethod
    async def find_by_id(self, id: UUID) -> Optional[WorkItem]:
        """Find work item by ID"""
        pass
    
    @abstractmethod
    async def find_open(self, component_id: str) -> Optional[WorkItem]:
        """Find open work item for component"""
        pass
    
    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> WorkItem:
        """Update work item status"""
        pass
    
    @abstractmethod
    async def list_active(self, page: int, limit: int) -> List[WorkItem]:
        """List active work items with pagination"""
        pass
    
    @abstractmethod
    async def count_active(self) -> int:
        """Count active work items"""
        pass
    
    @abstractmethod
    async def update_signal_count(self, id: UUID, count: int) -> WorkItem:
        """Update signal count for work item"""
        pass
    
    @abstractmethod
    async def add_rca(self, work_item_id: UUID, rca: RCA) -> WorkItem:
        """Add RCA to work item"""
        pass

class SignalRepository(ABC):
    """Abstract repository for Signal operations"""
    
    @abstractmethod
    async def save(self, signal: Signal) -> str:
        """Save signal to MongoDB"""
        pass
    
    @abstractmethod
    async def save_batch(self, signals: List[Signal]) -> List[str]:
        """Save multiple signals to MongoDB"""
        pass
    
    @abstractmethod
    async def find_by_work_item(self, work_item_id: UUID) -> List[Signal]:
        """Find all signals for a work item"""
        pass
    
    @abstractmethod
    async def link_to_work_item(self, signal_id: str, work_item_id: UUID) -> None:
        """Link signal to work item"""
        pass

class RCARepository(ABC):
    """Abstract repository for RCA operations"""
    
    @abstractmethod
    async def create(self, rca: RCA) -> RCA:
        """Create new RCA record"""
        pass
    
    @abstractmethod
    async def find_by_incident_id(self, incident_id: UUID) -> Optional[RCA]:
        """Find RCA by incident ID"""
        pass
    
    @abstractmethod
    async def update(self, rca: RCA) -> RCA:
        """Update existing RCA"""
        pass

class PostgresWorkItemRepository(WorkItemRepository):
    """PostgreSQL implementation of WorkItemRepository"""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def _row_to_work_item(self, row) -> WorkItem:
        """Convert database row to WorkItem object"""
        if not row:
            return None
            
        return WorkItem(
            id=row[0],
            component_id=row[1],
            component_type=ComponentType(row[2]),
            severity=Severity(row[3]),
            status=WorkItemStatus(row[4]),
            title=row[5],
            signal_count=row[6],
            created_at=row[7],
            updated_at=row[8],
            closed_at=row[9] if len(row) > 9 else None
        )

    @with_retry(max_attempts=3)
    async def create(self, signal: Signal) -> WorkItem:
        """Create work item from signal"""
        from sqlalchemy import text
        from uuid import uuid4
        
        new_id = uuid4()
        query = text("""
            INSERT INTO work_items (id, component_id, component_type, severity, status, title, signal_count)
            VALUES (:id, :component_id, :component_type, :severity, :status, :title, :signal_count)
            RETURNING id, component_id, component_type, severity, status, title,
                      signal_count, created_at, updated_at, closed_at
        """)
        
        try:
            result = await self.db_session.execute(query, {
                "id": new_id,
                "component_id": signal.component_id,
                "component_type": signal.component_type.value,
                "severity": signal.severity.value,
                "status": "OPEN",
                "title": f"{signal.severity.value} Issue: {signal.component_id}",
                "signal_count": 1
            })
            
            row = result.fetchone()
            await self.db_session.commit()
            
            return self._row_to_work_item(row)
        except Exception as e:
            await self.db_session.rollback()
            raise DatabaseError(f"Failed to create work item: {str(e)}")
    
    @with_retry(max_attempts=3)
    async def find_by_id(self, id: UUID) -> Optional[WorkItem]:
        """Find work item by ID"""
        from sqlalchemy import text
        
        query = text("""
            SELECT id, component_id, component_type, severity, status, title, 
                   signal_count, created_at, updated_at, closed_at
            FROM work_items WHERE id = :id
        """)
        
        result = await self.db_session.execute(query, {"id": id})
        row = result.fetchone()
        
        return self._row_to_work_item(row)
    
    @with_retry(max_attempts=3)
    async def find_open(self, component_id: str) -> Optional[WorkItem]:
        """Find open work item for component"""
        from sqlalchemy import text
        
        query = text("""
            SELECT id, component_id, component_type, severity, status, title,
                   signal_count, created_at, updated_at, closed_at
            FROM work_items 
            WHERE component_id = :component_id AND status IN ('OPEN', 'INVESTIGATING')
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = await self.db_session.execute(query, {"component_id": component_id})
        row = result.fetchone()
        
        return self._row_to_work_item(row)
    
    @with_retry(max_attempts=3)
    async def update_status(self, id: UUID, status: str) -> WorkItem:
        """Update work item status"""
        from sqlalchemy import text
        
        query = text("""
            UPDATE work_items 
            SET status = :status, updated_at = NOW()
            WHERE id = :id
            RETURNING id, component_id, component_type, severity, status, title,
                     signal_count, created_at, updated_at, closed_at
        """)
        
        try:
            result = await self.db_session.execute(query, {"id": id, "status": status})
            row = result.fetchone()
            await self.db_session.commit()
            
            if not row:
                raise DatabaseError(f"Work item {id} not found")
            
            return self._row_to_work_item(row)
        except Exception as e:
            await self.db_session.rollback()
            raise DatabaseError(f"Failed to update status: {str(e)}")
    
    @with_retry(max_attempts=3)
    async def list_active(self, page: int, limit: int) -> List[WorkItem]:
        """List active work items with pagination"""
        from sqlalchemy import text
        
        offset = (page - 1) * limit
        
        query = text("""
            SELECT id, component_id, component_type, severity, status, title,
                   signal_count, created_at, updated_at, closed_at
            FROM work_items 
            WHERE status != 'CLOSED'
            ORDER BY 
                CASE severity 
                    WHEN 'P0' THEN 1 
                    WHEN 'P1' THEN 2 
                    WHEN 'P2' THEN 3 
                    WHEN 'P3' THEN 4 
                END,
                created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await self.db_session.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()
        
        return [self._row_to_work_item(row) for row in rows]
    
    @with_retry(max_attempts=3)
    async def count_active(self) -> int:
        """Count active work items"""
        from sqlalchemy import text
        
        query = text("SELECT COUNT(*) FROM work_items WHERE status != 'CLOSED'")
        result = await self.db_session.execute(query)
        return result.scalar()
    
    @with_retry(max_attempts=3)
    async def update_signal_count(self, id: UUID, count: int) -> WorkItem:
        """Update signal count for work item"""
        from sqlalchemy import text
        
        query = text("""
            UPDATE work_items 
            SET signal_count = :signal_count, updated_at = NOW()
            WHERE id = :id
            RETURNING id, component_id, component_type, severity, status, title,
                     signal_count, created_at, updated_at, closed_at
        """)
        
        try:
            result = await self.db_session.execute(query, {"id": id, "signal_count": count})
            row = result.fetchone()
            await self.db_session.commit()
            
            if not row:
                raise DatabaseError(f"Work item {id} not found")
            
            return self._row_to_work_item(row)
        except Exception as e:
            await self.db_session.rollback()
            raise DatabaseError(f"Failed to update signal count: {str(e)}")
    
    @with_retry(max_attempts=3)
    async def add_rca(self, work_item_id: UUID, rca: RCA) -> WorkItem:
        """Add RCA to work item"""
        from sqlalchemy import text
        
        try:
            query = text("""
                UPDATE work_items 
                SET rca_id = :rca_id, rca_data = :rca_data, updated_at = NOW()
                WHERE id = :work_item_id
                RETURNING id, component_id, component_type, severity, status, title,
                         signal_count, created_at, updated_at, closed_at
            """)
            
            result = await self.db_session.execute(query, {
                "work_item_id": work_item_id,
                "rca_id": str(rca.id),
                "rca_data": rca.to_dict() if hasattr(rca, 'to_dict') else str(rca)
            })
            row = result.fetchone()
            await self.db_session.commit()
            
            return self._row_to_work_item(row)
        except Exception as e:
            await self.db_session.rollback()
            raise DatabaseError(f"Failed to add RCA: {str(e)}")

class PostgresRCARepository(RCARepository):
    """PostgreSQL implementation of RCARepository"""
    
    def __init__(self, db_session):
        self.db_session = db_session
        
    def _row_to_rca(self, row) -> Optional[RCA]:
        if not row:
            return None
        return RCA(
            id=row[0],
            incident_id=row[1],
            start_time=row[2],
            end_time=row[3],
            root_cause_category=RootCauseCategory(row[4]),
            fix_applied=row[5],
            prevention_steps=row[6],
            created_at=row[7],
            created_by=row[8]
        )

    @with_retry(max_attempts=3)
    async def create(self, rca: RCA) -> RCA:
        from sqlalchemy import text
        
        query = text("""
            INSERT INTO rca_records (id, work_item_id, start_time, end_time, root_cause_category, fix_applied, prevention_steps, mttr_minutes, created_by)
            VALUES (:id, :work_item_id, :start_time, :end_time, :root_cause_category, :fix_applied, :prevention_steps, :mttr_minutes, :created_by)
            RETURNING id, work_item_id, start_time, end_time, root_cause_category, fix_applied, prevention_steps, created_at, created_by
        """)
        
        try:
            result = await self.db_session.execute(query, {
                "id": rca.id,
                "work_item_id": rca.incident_id,
                "start_time": rca.start_time,
                "end_time": rca.end_time,
                "root_cause_category": rca.root_cause_category.value,
                "fix_applied": rca.fix_applied,
                "prevention_steps": rca.prevention_steps,
                "mttr_minutes": rca.mttr_minutes,
                "created_by": rca.created_by
            })
            row = result.fetchone()
            await self.db_session.commit()
            return self._row_to_rca(row)
        except Exception as e:
            await self.db_session.rollback()
            raise DatabaseError(f"Failed to create RCA: {str(e)}")

    @with_retry(max_attempts=3)
    async def find_by_incident_id(self, incident_id: UUID) -> Optional[RCA]:
        from sqlalchemy import text
        
        query = text("""
            SELECT id, work_item_id, start_time, end_time, root_cause_category, fix_applied, prevention_steps, created_at, created_by
            FROM rca_records WHERE work_item_id = :incident_id
        """)
        
        result = await self.db_session.execute(query, {"incident_id": incident_id})
        row = result.fetchone()
        return self._row_to_rca(row)

    @with_retry(max_attempts=3)
    async def update(self, rca: RCA) -> RCA:
        # Placeholder for update functionality
        return rca

class MongoSignalRepository(SignalRepository):
    """MongoDB implementation of SignalRepository"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.signals
    
    @with_retry(max_attempts=3)
    async def save(self, signal: Signal) -> str:
        """Save signal to MongoDB"""
        doc = {
            "component_id": signal.component_id,
            "component_type": signal.component_type.value,
            "severity": signal.severity.value,
            "message": signal.message,
            "timestamp": signal.timestamp,
            "metadata": signal.metadata,
            "work_item_id": str(signal.work_item_id) if signal.work_item_id else None,
            "ingested_at": signal.ingested_at or datetime.utcnow()
        }
        
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)
    
    @with_retry(max_attempts=3)
    async def save_batch(self, signals: List[Signal]) -> List[str]:
        """Save multiple signals to MongoDB"""
        docs = []
        for signal in signals:
            doc = {
                "component_id": signal.component_id,
                "component_type": signal.component_type.value,
                "severity": signal.severity.value,
                "message": signal.message,
                "timestamp": signal.timestamp,
                "metadata": signal.metadata,
                "work_item_id": str(signal.work_item_id) if signal.work_item_id else None,
                "ingested_at": signal.ingested_at or datetime.utcnow()
            }
            docs.append(doc)
        
        result = await self.collection.insert_many(docs)
        return [str(oid) for oid in result.inserted_ids]
    
    @with_retry(max_attempts=3)
    async def find_by_work_item(self, work_item_id: UUID) -> List[Signal]:
        """Find all signals for a work item"""
        cursor = self.collection.find(
            {"work_item_id": str(work_item_id)}
        ).sort("timestamp", -1)
        
        signals = []
        async for doc in cursor:
            signal = Signal(
                id=str(doc["_id"]),
                component_id=doc["component_id"],
                component_type=ComponentType(doc["component_type"]),
                severity=Severity(doc["severity"]),
                message=doc["message"],
                timestamp=doc["timestamp"],
                metadata=doc.get("metadata", {}),
                work_item_id=UUID(doc["work_item_id"]) if doc["work_item_id"] else None,
                ingested_at=doc.get("ingested_at")
            )
            signals.append(signal)
        
        return signals
    
    @with_retry(max_attempts=3)
    async def link_to_work_item(self, signal_id: str, work_item_id: UUID) -> None:
        """Link signal to work item"""
        from bson import ObjectId
        
        await self.collection.update_one(
            {"_id": ObjectId(signal_id)},
            {"$set": {"work_item_id": str(work_item_id)}}
        )
