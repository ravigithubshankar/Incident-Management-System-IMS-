from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database URLs
    database_url: str = "postgresql+asyncpg://neondb_owner:npg_fP2vJcYSULj5@ep-dark-glade-apdj1c27.c-7.us-east-1.aws.neon.tech/neondb?ssl=require"
    mongo_uri: str = "mongodb://localhost:27017/ims_signals"
    redis_url: str = "redis://localhost:6379"
    
    # Security
    jwt_secret: str = "supersecretkey"
    api_key: str = "dev-api-key-12345"
    
    # Rate limiting
    rate_limit_capacity: int = 10000
    rate_limit_refill_rate: int = 10000  # tokens per second
    
    # Queue settings
    queue_max_size: int = 50000
    worker_count: int = 20
    batch_size: int = 500
    
    # Debounce settings
    debounce_window_seconds: int = 10
    
    # WebSocket settings
    ws_ping_interval: int = 20
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
