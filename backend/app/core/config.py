import json
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./visaready.db", alias="DATABASE_URL")
    cors_origins: list[str] = ["*"]
    api_rate_limit_per_minute: int = Field(default=120, alias="API_RATE_LIMIT_PER_MINUTE")
    admin_api_key: str = Field(default="dev-admin-key", alias="ADMIN_API_KEY")
    stale_threshold_minutes: int = Field(default=30, alias="STALE_THRESHOLD_MINUTES")
    checker_interval_minutes: int = Field(default=30, alias="CHECKER_INTERVAL_MINUTES")
    alert_webhook_url: str | None = Field(default=None, alias="ALERT_WEBHOOK_URL")
    country_importance_json: str = Field(default='{}', alias='COUNTRY_IMPORTANCE_JSON')

    @property
    def country_importance(self) -> dict[str, int]:
        try:
            return json.loads(self.country_importance_json)
        except Exception:
            return {}

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
