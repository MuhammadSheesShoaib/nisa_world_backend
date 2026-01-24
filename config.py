from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str
    
    # JWT Configuration
    JWT_SECRET_KEY: Optional[str] = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    # JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # CORS Configuration
    CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env (like old SUPABASE_* vars)


settings = Settings()

