import asyncio
import time
from collections import defaultdict
from typing import Dict
import structlog

logger = structlog.get_logger()

class ThroughputCounter:
    """Thread-safe throughput counter for metrics"""
    
    def __init__(self):
        self.counts = defaultdict(int)
        self.last_reset = time.time()
        self.lock = asyncio.Lock()
    
    async def increment(self, metric_name: str = "signals") -> None:
        """Increment counter for a metric"""
        async with self.lock:
            self.counts[metric_name] += 1
    
    async def get_rate(self, metric_name: str = "signals") -> float:
        """Get rate per second for a metric"""
        async with self.lock:
            current_time = time.time()
            time_elapsed = current_time - self.last_reset
            
            if time_elapsed == 0:
                return 0.0
            
            rate = self.counts[metric_name] / time_elapsed
            return rate
    
    async def reset(self) -> None:
        """Reset all counters"""
        async with self.lock:
            self.counts.clear()
            self.last_reset = time.time()

# Global counter instance
throughput_counter = ThroughputCounter()

async def increment_signal_count():
    """Increment signal processing count"""
    await throughput_counter.increment("signals")

async def get_signal_rate() -> float:
    """Get current signal processing rate"""
    return await throughput_counter.get_rate("signals")

async def get_queue_depth() -> int:
    """Get current queue depth"""
    from app.workers.queue_worker import signal_queue
    return signal_queue.qsize()

async def get_worker_utilisation() -> str:
    """Get worker utilization (busy/total)"""
    # This is a simplified version - in production you'd track actual worker state
    from app.core.config import settings
    queue_depth = await get_queue_depth()
    
    # Estimate busy workers based on queue depth
    busy_workers = min(queue_depth // 10 + 1, settings.worker_count)
    
    return f"{busy_workers}/{settings.worker_count}"
