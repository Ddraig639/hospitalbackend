from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Hospital Management System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://hospitaladm:1BL8H14b8MSbr5UQBSNmIbG6VSSZwi0Y@dpg-d4mk32khg0os73bt93p0-a.oregon-postgres.render.com/hospitla_db"
    )

    # Security
    SECRET_KEY: str = "ZUW-sUh_NV2bqMwBhCCwBCTkSvKhL-6lbQym2QKiLwg"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
