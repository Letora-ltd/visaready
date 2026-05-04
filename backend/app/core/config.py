import os
from pydantic_settings import BaseSettings
from pydantic import Field

# Use relative path for SQLite to ensure it works on Vercel when committed
# On Vercel, the app root is /var/task
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(base_dir, "visaready.db")
default_db = f"sqlite:///{db_path}"

class Settings(BaseSettings):
    database_url: str = Field(default=default_db, alias="DATABASE_URL")
    cors_origins: list[str] = ["*"]
    api_rate_limit_per_minute: int = Field(default=120, alias="API_RATE_LIMIT_PER_MINUTE")
    admin_api_key: str = Field(default="dev-admin-key", alias="ADMIN_API_KEY")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
