from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger()

class IMSException(Exception):
    """Base exception for Incident Management System"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail

class DatabaseError(IMSException):
    """Raised when database operations fail"""
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

class ValidationException(IMSException):
    """Raised when data validation fails"""
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return structured JSON"""
    if isinstance(exc, IMSException):
        logger.error(
            "IMS_EXCEPTION",
            path=request.url.path,
            status_code=exc.status_code,
            message=exc.message,
            detail=exc.detail
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "detail": exc.detail
            }
        )
    
    # Log the full traceback for unhandled exceptions
    logger.exception(
        "UNHANDLED_EXCEPTION",
        path=request.url.path,
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred. Our engineers have been alerted.",
            "path": request.url.path
        }
    )
