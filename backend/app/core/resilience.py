import asyncio
import functools
from typing import Type, Tuple, Callable, Any
import structlog

logger = structlog.get_logger()

def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Retry decorator for async functions with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_base: Base for exponential backoff calculation
        exceptions: Tuple of exception types to retry on
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(
                            "retry_failed",
                            function=fn.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(e)
                        )
                        raise
                    
                    wait_time = backoff_base ** attempt
                    logger.warning(
                        "retry_attempt",
                        function=fn.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator
