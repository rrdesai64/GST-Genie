from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn, validator
from typing import List, Optional
import logging
from enum import Enum

class EnvironmentEnum(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

class Settings(BaseSettings):
    # Environment
    environment: EnvironmentEnum = Field(default=EnvironmentEnum.DEVELOPMENT)
    
    # Database
    database_url: PostgresDsn = Field(default="postgresql+asyncpg://user:password@localhost/gemini_chat")
    
    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379")
    redis_password: Optional[str] = None
    
    # Gemini API
    gemini_api_key: str = Field(..., min_length=1)
    gemini_model: str = Field(default="gemini-pro")
    
    # Authentication
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    
    # Application
    max_context_length: int = Field(default=4000, ge=1000)
    max_messages_per_session: int = Field(default=100, ge=10)
    session_timeout_hours: int = Field(default=24, ge=1)
    
    # CORS
    allowed_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    
    # Logging
    log_level: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        env_prefix = "CHAT_"
        case_sensitive = False

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

settings = Settings()