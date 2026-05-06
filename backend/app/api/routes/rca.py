from fastapi import APIRouter, HTTPException, status, Request, Depends
from uuid import UUID
from datetime import datetime
import structlog

from app.domain.schemas import RCACreate, RCAResponse, ErrorResponse
from app.domain.models import RCA, RootCauseCategory
from app.services.lifecycle import LifecycleService
from app.core.security import get_api_key_from_header, API_KEYS
from app.core.exceptions import ValidationException

logger = structlog.get_logger()

router = APIRouter()

from app.core.security import validate_api_key

@router.post("/incidents/{incident_id}/rca", response_model=RCAResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_rca(
    incident_id: str,
    rca_data: RCACreate,
    request: Request,
    _: bool = Depends(validate_api_key)
):
    """
    Create or update RCA for an incident.
    Validates that RCA is complete.
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
        
        # Create RCA object
        rca = RCA(
            id=UUID(),  # Generate new ID
            incident_id=incident_uuid,
            start_time=rca_data.start_time,
            end_time=rca_data.end_time,
            root_cause_category=rca_data.root_cause_category,
            fix_applied=rca_data.fix_applied,
            prevention_steps=rca_data.prevention_steps,
            created_at=datetime.utcnow(),
            created_by=rca_data.created_by
        )
        
        # Validate RCA completeness
        if not rca.is_complete():
            raise ValidationException(
                "RCA is incomplete. All fields must be filled and fix_applied/prevention_steps must be at least 50 characters."
            )
        
        # Use lifecycle service to add RCA
        lifecycle_service = LifecycleService()
        work_item = await lifecycle_service.add_rca(incident_uuid, rca)
        
        # Return RCA response
        response = RCAResponse(
            id=rca.id,
            incident_id=rca.incident_id,
            start_time=rca.start_time,
            end_time=rca.end_time,
            root_cause_category=rca.root_cause_category,
            fix_applied=rca.fix_applied,
            prevention_steps=rca.prevention_steps,
            mttr_minutes=rca.mttr_minutes,
            created_at=rca.created_at,
            created_by=rca.created_by,
            is_complete=rca.is_complete()
        )
        
        logger.info(
            "RCA created successfully",
            incident_id=incident_id,
            rca_id=str(rca.id),
            mttr_minutes=rca.mttr_minutes
        )
        
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create RCA",
            incident_id=incident_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create RCA"
        )

@router.get("/incidents/{incident_id}/rca", response_model=RCAResponse)
async def get_rca(
    incident_id: str,
    request: Request,
    _: bool = Depends(validate_api_key)
):
    """
    Retrieve RCA for an incident including MTTR calculation.
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
        
        # Get work item from repository
        from app.patterns.repository import PostgresWorkItemRepository
        from app.db.postgres import get_postgres_session
        
        async with get_postgres_session() as session:
            work_item_repo = PostgresWorkItemRepository(session)
            
            work_item = await work_item_repo.find_by_id(incident_uuid)
            if not work_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Incident not found"
                )
        
        if not work_item.rca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RCA not found for this incident"
            )
        
        # Return RCA response
        response = RCAResponse(
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
        
        logger.info(
            "RCA retrieved successfully",
            incident_id=incident_id,
            rca_id=str(work_item.rca.id),
            mttr_minutes=work_item.rca.mttr_minutes
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve RCA",
            incident_id=incident_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve RCA"
        )
