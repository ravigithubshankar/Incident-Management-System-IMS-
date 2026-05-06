from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List

from app.domain.models import Signal, ComponentType, Severity
from app.domain.schemas import SignalPayload

class SignalFactory:
    """Factory for creating Signal objects"""
    
    @staticmethod
    def create_from_payload(payload: SignalPayload) -> Signal:
        """Create Signal from API payload (Pydantic model)"""
        return Signal(
            id=str(uuid4()),
            component_id=payload.component_id,
            component_type=ComponentType(payload.component_type.value),
            severity=Severity(payload.severity.value),
            message=payload.message,
            timestamp=payload.timestamp,
            metadata=payload.metadata,
            ingested_at=datetime.utcnow()
        )
    
    @staticmethod
    def create_batch_from_payloads(payloads: List[SignalPayload]) -> List[Signal]:
        """Create multiple Signals from API payloads"""
        return [SignalFactory.create_from_payload(payload) for payload in payloads]
