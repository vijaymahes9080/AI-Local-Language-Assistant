from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "LingoSphere AI"
    API_V1_STR: str = "/api/v1"
    
    # Security & Authentication
    SECRET_KEY: str = "lingosphere-super-secret-key-for-jwt-signing-2026-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Database
    # Fallback to sqlite+aiosqlite if postgres is not available during local tests
    DATABASE_URL: str = "sqlite+aiosqlite:///./lingosphere.db"
    
    # AI Engine Keys (Optional: fallbacks to simulated models if keys are empty)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    # System Preferences
    DEFAULT_LANGUAGE: str = "english"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
