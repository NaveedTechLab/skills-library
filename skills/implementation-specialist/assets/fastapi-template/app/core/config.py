from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
