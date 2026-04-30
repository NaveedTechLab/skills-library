from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    PROJECT_NAME: str = "FastAPI App"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/dbname"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_HOSTS: list[str] = ["*"]


settings = Settings()
