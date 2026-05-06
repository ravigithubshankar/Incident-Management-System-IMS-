from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from uuid import UUID
import structlog

from app.domain.schemas import (
    WorkItemResponse, 
    WorkItemDetail, 
    StatusUpdateRequest,
    ErrorResponse
)
from app.patterns.repository import PostgresWorkItemRepository, MongoSignalRepository
from app.services.lifecycle import LifecycleService
from app.db.postgres import get_postgres_session
from app.db.mongo import get_mongo_db
from app.core.security import get_api_key_from_header, API_KEYS

logger = structlog.get_logger()

router = APIRouter()

from app.core.security import validate_api_key

@router.get("/incidents", response_model=List[WorkItemResponse])
async def list_incidents(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    _: bool = Depends(validate_api_key)
):
    """
    List active incidents sorted by severity (P0→P3) with cursor pagination.
    """
    try:
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            work_items = await work_item_repo.list_active(page, limit)
            
            # Convert to response format
            responses = [
                WorkItemResponse(
                    id=item.id,
                    component_id=item.component_id,
                    component_type=item.component_type,
                    severity=item.severity,
                    status=item.status,
                    title=item.title,
                    signal_count=item.signal_count,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    closed_at=item.closed_at
                )
                for item in work_items
            ]
            
            logger.info(
                "Retrieved active incidents",
                page=page,
                limit=limit,
                count=len(responses)
            )
            
            return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list incidents", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve incidents"
        )

@router.get("/incidents/{incident_id}", response_model=WorkItemDetail)
async def get_incident_detail(
    incident_id: str,
    request: Request,
    _: bool = Depends(validate_api_key)
):
    """
    Get incident detail including linked signals and RCA if exists.
    """
    try:
        # Validate UUID format
        try:
            incident_uuid = UUID(incident_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid incident ID format"
            )
        
        # Get work item
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            
            work_item = await work_item_repo.find_by_id(incident_uuid)
            if not work_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Incident not found"
                )
        
        # Get signals for this work item
        mongo_db = await get_mongo_db()
        signal_repo = MongoSignalRepository(mongo_db)
        signals = await signal_repo.find_by_work_item(incident_uuid)
        
        # Convert signals to response format
        from app.domain.schemas import SignalResponse
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
        
        # Get RCA if exists
        rca_response = None
        if work_item.rca:
            from app.domain.schemas import RCAResponse
            rca_response = RCAResponse(
                id=work_item.rca.id,
                incident_id=work_item.rca.incident_id,
                start_time=work_item.rca.start_time,
                end_time=work_item.rca.end_time,
                root_cause_category=work_item.rca.root_cause_category,
                fix_applied=work_item.rca.fix_applied,
                prevention_steps=work_item.rca.prevention_steps,
                mttr_minutes=work_item.rca.mttr_minutes,
                created_at=work_item.rca.created_at,
                created_by=work_item.rca.created_by,
                is_complete=work_item.rca.is_complete()
            )
        
        # Build response
        response = WorkItemDetail(
            id=work_item.id,
            component_id=work_item.component_id,
            component_type=work_item.component_type,
            severity=work_item.severity,
            status=work_item.status,
            title=work_item.title,
            signal_count=work_item.signal_count,
            created_at=work_item.created_at,
            updated_at=work_item.updated_at,
            closed_at=work_item.closed_at,
            signals=signal_responses,
            rca=rca_response
        )
        
        logger.info(
            "Retrieved incident detail",
            incident_id=incident_id,
            signal_count=len(signal_responses),
            has_rca=rca_response is not None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get incident detail",
            incident_id=incident_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve incident detail"
        )

@router.patch("/incidents/{incident_id}/status", response_model=WorkItemResponse)
async def update_incident_status(
    incident_id: str,
    status_update: StatusUpdateRequest,
    request: Request,
    _: bool = Depends(validate_api_key)
):
    """
    Update incident status with state machine enforcement.
    """
    try:
        # Validate UUID format
        try:
            incident_uuid = UUID(incident_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid incident ID format"
            )
        
        # Use lifecycle service for state machine validation
        lifecycle_service = LifecycleService()
        updated_work_item = await lifecycle_service.transition_status(
            incident_uuid, 
            status_update.status.value
        )
        
        # Convert to response format
        response = WorkItemResponse(
            id=updated_work_item.id,
            component_id=updated_work_item.component_id,
            component_type=updated_work_item.component_type,
            severity=updated_work_item.severity,
            status=updated_work_item.status,
            title=updated_work_item.title,
            signal_count=updated_work_item.signal_count,
            created_at=updated_work_item.created_at,
            updated_at=updated_work_item.updated_at,
            closed_at=updated_work_item.closed_at
        )
        
        logger.info(
            "Incident status updated",
            incident_id=incident_id,
            new_status=status_update.status.value
        )
        
        return response
        
    except ValueError as e:
        # Handle state machine validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update incident status",
            incident_id=incident_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update incident status"
        )

@router.delete("/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: str,
    request: Request,
    _: bool = Depends(validate_api_key)
):
    """
    Soft delete incident (admin only).
    """
    try:
        # Validate UUID format
        try:
            incident_uuid = UUID(incident_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid incident ID format"
            )
        
        # For now, this is a placeholder for admin functionality
        # In production, you'd implement proper soft delete with permissions
        logger.warning(
            "Incident delete requested (not implemented)",
            incident_id=incident_id
        )
        
        # Return 204 as if deleted (placeholder)
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete incident",
            incident_id=incident_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete incident"
        )
