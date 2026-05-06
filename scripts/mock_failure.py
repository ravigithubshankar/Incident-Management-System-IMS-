#!/usr/bin/env python3
"""
Mock failure simulation script for Incident Management System

Simulates:
  t=0s  → 100 × RDBMS_PRIMARY_01 P0 signals  → expect 1 Work Item (debounced)
  t=5s  → 50  × MCP_HOST_02 P1 signals        → expect 1 Work Item (debounced)
  t=12s → verify /health and /api/v1/incidents
"""

import asyncio
import httpx
import json
from datetime import datetime, timezone

TARGET = "http://localhost:8000"
HEADERS = {"X-API-Key": "dev-api-key-12345", "Content-Type": "application/json"}

async def send_burst(component_id, component_type, severity, count, delay=0):
    """Send a burst of signals for testing"""
    await asyncio.sleep(delay)
    
    signals = [
        {
            "component_id": component_id,
            "component_type": component_type,
            "severity": severity,
            "message": f"Simulated failure #{i} on {component_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"sim": True, "index": i}
        }
        for i in range(count)
    ]
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TARGET}/api/v1/signals", 
            json=signals, 
            headers=HEADERS, 
            timeout=30
        )
        print(f"[{component_id}] Sent {count} signals → {resp.status_code}")

async def main():
    """Main simulation function"""
    print("Starting cascading failure simulation...")
    
    # Run simulations in parallel
    await asyncio.gather(
        send_burst("RDBMS_PRIMARY_01", "RDBMS", "P0", 100, delay=0),
        send_burst("MCP_HOST_02", "MCP_HOST", "P1", 50, delay=5),
    )
    
    # Wait for processing
    await asyncio.sleep(3)
    
    # Verify results
    async with httpx.AsyncClient() as client:
        # Check health
        h = await client.get(f"{TARGET}/health", headers=HEADERS)
        print(f"\nHealth: {json.dumps(h.json(), indent=2)}")
        
        # Check incidents
        r = await client.get(f"{TARGET}/api/v1/incidents", headers=HEADERS)
        print(f"\nActive incidents: {json.dumps(r.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
