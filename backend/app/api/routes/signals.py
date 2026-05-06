from typing import List
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
import structlog

from app.domain.schemas import SignalPayload, SignalResponse, BulkSignalResponse, ErrorResponse
from app.patterns.factory import SignalFactory
from app.workers.queue_worker import signal_queue
from app.core.security import get_api_key_from_header, API_KEYS
import hashlib

logger = structlog.get_logger()

router = APIRouter()

from app.core.security import validate_api_key

@router.post("/signals", response_model=BulkSignalResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_signals(
    request: Request,
    payloads: List[SignalPayload] | SignalPayload,
    _: bool = Depends(validate_api_key)
):
    """
    Ingest single signal or array of signals.
    Returns 202 Accepted for successful ingestion.
    """
    try:
        # Normalize to list
        if isinstance(payloads, SignalPayload):
            payloads = [payloads]
        
        # Convert payloads to Signal objects
        signals = SignalFactory.create_batch_from_payloads(payloads)
        
        accepted = 0
        rejected = 0
        errors = []
        
        # Try to queue each signal
        for signal in signals:
            try:
                signal_queue.put_nowait(signal)
                accepted += 1
            except Exception as e:
                rejected += 1
                if "QueueFull" in str(type(e)) or "queue" in str(e).lower():
                    errors.append("Queue full - backpressure applied")
                else:
                    errors.append(f"Failed to queue signal: {str(e)}")
        
        # If any were rejected due to backpressure, return 429
        if rejected > 0 and any("backpressure" in error for error in errors):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "backpressure", "retry_after": 1},
                headers={"Retry-After": "1"}
            )
        
        logger.info(
            "Signals ingested successfully",
            accepted=accepted,
            rejected=rejected,
            total=len(signals)
        )
        
        return BulkSignalResponse(
            accepted=accepted,
            rejected=rejected,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Signal ingestion failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signal ingestion"
        )

@router.get("/signals/{work_item_id}", response_model=List[SignalResponse])
async def get_signals_for_work_item(
    work_item_id: str,
    _: bool = Depends(validate_api_key)
):
    """
    Get all raw signals for a specific work item.
    """
    try:
        from uuid import UUID
        from app.patterns.repository import MongoSignalRepository
        from app.db.mongo import get_mongo_db
        
        # Validate UUID format
        try:
            work_item_uuid = UUID(work_item_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid work item ID format"
            )
        
        # Get signals from MongoDB
        mongo_db = await get_mongo_db()
        signal_repo = MongoSignalRepository(mongo_db)
        
        signals = await signal_repo.find_by_work_item(work_item_uuid)
        
        # Convert to response format
        signal_responses = [
            SignalResponse(
                id=signal.id,
                component_id=signal.component_id,
                component_type=signal.component_type,
                severity=signal.severity,
                message=signal.message,
                timestamp=signal.timestamp,
                metadata=signal.metadata,
                work_item_id=signal.work_item_id,
                ingested_at=signal.ingested_at
            )
            for signal in signals
        ]
        
        logger.info(
            "Retrieved signals for work item",
            work_item_id=work_item_id,
            signal_count=len(signal_responses)
        )
        
        return signal_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve signals for work item",
            work_item_id=work_item_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve signals"
        )
