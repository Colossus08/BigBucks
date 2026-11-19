from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./finance.db"
    gross_annual_salary: Decimal = Decimal("58193.00")
    pay_frequency: str = "fortnightly"
    super_rate: Decimal = Decimal("0.12")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auth_username: str = ""
    auth_password: str = ""
    auth_secret: str = "dev-secret-change-in-prod"
    auth_token_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
