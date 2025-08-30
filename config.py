from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(15, alias="JWT_EXPIRE_MINUTES")
    web_origin: str = Field("http://localhost:5173", alias="WEB_ORIGIN")
    admin_emails: str = Field("", alias="ADMIN_EMAILS")

    # Optional Redis demo toggle
    use_redis: bool = Field(False, alias="USE_REDIS")
    redis_url: str | None = Field(None, alias="REDIS_URL")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()


