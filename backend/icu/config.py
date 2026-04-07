from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ICU_", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://icu:icu@localhost:5432/icu",
        description="Async SQLAlchemy URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://icu:icu@localhost:5432/icu",
        description="Sync URL for Alembic",
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    otp_pepper: str = "dev-otp-pepper"
    otp_ttl_seconds: int = 600
    otp_cooldown_seconds: int = 60
    otp_max_per_hour: int = 5
    otp_max_attempts: int = 5
    otp_lock_seconds: int = 900

    cors_origins: str = "http://localhost:3000"

    dev_log_otp: bool = True

    # Optional: Resend.com API (https://resend.com) for transactional email
    resend_api_key: str | None = None
    resend_from_email: str | None = None

    log_json: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
