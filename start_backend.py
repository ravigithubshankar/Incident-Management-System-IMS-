#!/usr/bin/env python3
"""
Simple backend startup script for testing without Docker
"""
import os
import sys
import subprocess
import time

def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run([
            r"C:\Program Files\Docker\Docker\resources\bin\docker.exe", 
            "version"
        ], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def start_backend_local():
    """Start backend locally without databases"""
    print("Starting backend locally (without databases)...")
    
    # Set environment variables for local development
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": "sqlite:///./test.db",  # Use SQLite for testing
        "MONGO_URI": "mongodb://localhost:27017/ims_signals",
        "REDIS_URL": "redis://localhost:6379",
        "JWT_SECRET": "supersecretkey",
        "API_KEY": "dev-api-key-12345"
    })
    
    # Start uvicorn
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ], env=env)
    except KeyboardInterrupt:
        print("\nBackend stopped.")

def main():
    """Main startup logic"""
    print("=== Incident Management System Startup ===")
    
    if check_docker():
        print("✓ Docker is available")
        print("To start with Docker: docker compose up postgres mongo redis -d")
        print("Then run: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("✗ Docker not available")
        print("Starting backend locally...")
    
    print("\nStarting backend server...")
    start_backend_local()
    
    print("\nBackend should be available at: http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("Health check: http://localhost:8000/health")

if __name__ == "__main__":
    main()
