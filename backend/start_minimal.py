#!/usr/bin/env python3
"""
Ultra-minimal FastAPI server for testing - no databases at all
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Incident Management System - Minimal", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Incident Management System API", "status": "running"}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "postgres": "not_available",
        "mongo": "not_available", 
        "redis": "not_available"
    }

@app.get("/api/v1/incidents")
async def get_incidents():
    """Mock incidents endpoint"""
    return [
        {
            "id": "test-1",
            "component_id": "TEST_COMPONENT",
            "component_type": "API",
            "severity": "P1",
            "status": "OPEN",
            "title": "Test Incident",
            "signal_count": 5,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }
    ]

@app.get("/docs")
async def docs_redirect():
    return {"message": "API docs available at /docs"}

if __name__ == "__main__":
    print("Starting minimal backend server...")
    print("Available at: http://localhost:8000")
    print("Health check: http://localhost:8000/health")
    print("API docs: http://localhost:8000/docs")
    print("Mock incidents: http://localhost:8000/api/v1/incidents")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8002)
