import pytest
import asyncio
from app.core.rate_limiter import TokenBucket


class TestRateLimiter:
    """Test token bucket rate limiter"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_capacity(self):
        """Test that rate limiter allows requests within capacity"""
        bucket = TokenBucket(capacity=100, refill_rate=100)
        
        # Should allow first 100 requests
        for _ in range(100):
            result = await bucket.consume()
            assert result is True
        
        # Should be empty now
        assert bucket.tokens == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_refills_over_time(self):
        """Test that rate limiter refills tokens over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10)  # 10 tokens per second
        
        # Consume all tokens
        for _ in range(10):
            await bucket.consume()
        assert bucket.tokens == 0
        
        # Wait 0.1 seconds - should get 1 token back
        await asyncio.sleep(0.11)  # Slightly more than 0.1s
        result = await bucket.consume()
        assert result is True
        assert bucket.tokens == 0  # Consumed the refilled token
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_empty(self):
        """Test that rate limiter blocks when tokens are empty"""
        bucket = TokenBucket(capacity=5, refill_rate=5)
        
        # Consume all tokens
        for _ in range(5):
            await bucket.consume()
        
        # Next request should be blocked
        result = await bucket.consume()
        assert result is False
        assert bucket.tokens == 0
    
    @pytest.mark.asyncio
    async def test_10001_request_returns_429(self):
        """Test that 10001st request returns False (simulates 429)"""
        bucket = TokenBucket(capacity=10000, refill_rate=10000)
        
        # Consume 10000 tokens
        for _ in range(10000):
            result = await bucket.consume()
            assert result is True
        
        # 10001st request should be blocked
        result = await bucket.consume()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_concurrent_access_is_thread_safe(self):
        """Test that concurrent access is thread-safe"""
        bucket = TokenBucket(capacity=100, refill_rate=100)
        
        async def consumer():
            results = []
            for _ in range(50):
                result = await bucket.consume()
                results.append(result)
            return results
        
        # Run multiple consumers concurrently
        tasks = [consumer() for _ in range(5)]
        all_results = await asyncio.gather(*tasks)
        
        # Flatten all results
        flat_results = []
        for results in all_results:
            flat_results.extend(results)
        
        # Should have exactly 250 results (5 * 50)
        assert len(flat_results) == 250
        
        # First 100 should be True, rest should be False
        true_count = sum(1 for r in flat_results if r)
        assert true_count == 100
        
        # Should not raise any exceptions
        assert all(isinstance(r, bool) for r in flat_results)
