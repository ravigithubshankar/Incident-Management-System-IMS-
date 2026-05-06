import pytest
import asyncio

from app.core.resilience import with_retry


class TestRetry:
    """Test retry decorator functionality"""
    
    async def test_retry_succeeds_second_attempt(self):
        """Test retry succeeds on second attempt"""
        call_count = 0
        
        @with_retry(max_attempts=3)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("fail")
            return "success"
        
        result = await flaky_function()
        assert result == "success"
        assert call_count == 2
    
    async def test_retry_succeeds_first_attempt(self):
        """Test retry succeeds on first attempt"""
        call_count = 0
        
        @with_retry(max_attempts=3)
        async def stable_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await stable_function()
        assert result == "success"
        assert call_count == 1
    
    async def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts and raises exception"""
        call_count = 0
        
        @with_retry(max_attempts=3)
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("always fail")
        
        with pytest.raises(Exception, match="always fail"):
            await always_failing_function()
        
        assert call_count == 3
    
    async def test_retry_with_custom_backoff(self):
        """Test retry with custom backoff"""
        call_count = 0
        wait_times = []
        
        @with_retry(max_attempts=3, backoff_base=2.0)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("fail")
            return "success"
        
        # Mock sleep to capture wait times
        original_sleep = asyncio.sleep
        captured_waits = []
        
        async def mock_sleep(delay):
            captured_waits.append(delay)
            return await original_sleep(delay)
        
        # Patch asyncio.sleep temporarily
        import asyncio
        asyncio.sleep = mock_sleep
        
        try:
            result = await flaky_function()
            assert result == "success"
            assert call_count == 2
            # Should have waited once (after first failure)
            assert len(captured_waits) == 1
            # Wait time should be backoff_base ** attempt_number = 2.0 ** 0 = 1.0
            assert captured_waits[0] == 1.0
        finally:
            # Restore original sleep
            asyncio.sleep = original_sleep
    
    async def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exception types"""
        call_count = 0
        
        @with_retry(max_attempts=3, exceptions=(ValueError,))
        async def function_with_value_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("value error")
            return "success"
        
        result = await function_with_value_error()
        assert result == "success"
        assert call_count == 2
    
    async def test_retry_ignores_other_exceptions(self):
        """Test retry ignores non-specified exception types"""
        @with_retry(max_attempts=3, exceptions=(ValueError,))
        async def function_with_type_error():
            raise TypeError("type error")
        
        with pytest.raises(TypeError, match="type error"):
            await function_with_type_error()
