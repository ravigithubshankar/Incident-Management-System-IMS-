from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum

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

class SignalPayload(BaseModel):
    component_id: str = Field(..., min_length=1, max_length=100)
    component_type: ComponentType
    severity: Severity
    message: str = Field(..., min_length=1, max_length=1000)
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"  # Strict validation - no extra fields allowed

class SignalResponse(BaseModel):
    id: str
    component_id: str
    component_type: ComponentType
    severity: Severity
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    work_item_id: Optional[UUID] = None
    ingested_at: Optional[datetime] = None

class WorkItemCreate(BaseModel):
    component_id: str = Field(..., min_length=1, max_length=100)
    component_type: ComponentType
    severity: Severity
    title: str = Field(..., min_length=1, max_length=500)

class WorkItemResponse(BaseModel):
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

class WorkItemDetail(WorkItemResponse):
    signals: List[SignalResponse] = []
    rca: Optional['RCAResponse'] = None

class StatusUpdateRequest(BaseModel):
    status: WorkItemStatus

class RCACreate(BaseModel):
    start_time: datetime
    end_time: datetime
    root_cause_category: RootCauseCategory
    fix_applied: str = Field(..., min_length=50, max_length=2000)
    prevention_steps: str = Field(..., min_length=50, max_length=2000)
    created_by: str = Field(..., min_length=1, max_length=100)

    @validator('end_time')
    def end_time_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class RCAResponse(BaseModel):
    id: UUID
    incident_id: UUID
    start_time: datetime
    end_time: datetime
    root_cause_category: RootCauseCategory
    fix_applied: str
    prevention_steps: str
    mttr_minutes: float
    created_at: datetime
    created_by: str
    is_complete: bool

class HealthCheck(BaseModel):
    status: str
    postgres: str
    mongo: str
    redis: str

class MetricsResponse(BaseModel):
    signals_per_sec: float
    queue_depth: int
    active_incidents: int
    worker_utilisation: str

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

class BulkSignalResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[str] = []

# Forward reference resolution
WorkItemDetail.model_rebuild()

# Update RCAResponse to include forward reference
RCAResponse.update_forward_refs()
