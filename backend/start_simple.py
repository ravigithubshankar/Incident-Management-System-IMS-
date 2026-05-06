#!/usr/bin/env python3
"""
Simple backend startup without databases for testing
"""
import os
import sys
import uvicorn

# Set environment variables for local development without databases
os.environ.update({
    "DATABASE_URL": "sqlite:///./test.db",  # Use SQLite instead
    "MONGO_URI": "mongodb://localhost:27017/ims_signals",
    "REDIS_URL": "redis://localhost:6379",
    "JWT_SECRET": "supersecretkey",
    "API_KEY": "dev-api-key-12345"
})

from app.main import app

if __name__ == "__main__":
    print("Starting backend without databases...")
    print("Backend will be available at: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print()
    print("Note: Using SQLite instead of PostgreSQL/MongoDB/Redis")
    print()
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\nBackend stopped.")
