from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(default="sqlite:///./visaready.db", alias="DATABASE_URL")
    cors_origins: list[str] = ["*"]
    api_rate_limit_per_minute: int = Field(default=120, alias="API_RATE_LIMIT_PER_MINUTE")
    admin_api_key: str = Field(default="dev-admin-key", alias="ADMIN_API_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
