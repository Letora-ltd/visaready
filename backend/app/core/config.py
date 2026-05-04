import os
import shutil
from pydantic_settings import BaseSettings
from pydantic import Field

# Vercel handling for SQLite
# We copy the pre-seeded DB from the read-only /var/task to the writable /tmp
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
source_db = os.path.join(base_dir, "visaready.db")
target_db = "/tmp/visaready.db"

if os.environ.get("VERCEL"):
    if os.path.exists(source_db) and not os.path.exists(target_db):
        try:
            shutil.copy2(source_db, target_db)
            print(f"Database copied to {target_db}")
        except Exception as e:
            print(f"Failed to copy database: {e}")
    default_db = f"sqlite:///{target_db}"
else:
    default_db = f"sqlite:///{source_db}"

class Settings(BaseSettings):
    database_url: str = Field(default=default_db, alias="DATABASE_URL")
    cors_origins: list[str] = ["*"]
    api_rate_limit_per_minute: int = Field(default=120, alias="API_RATE_LIMIT_PER_MINUTE")
    admin_api_key: str = Field(default="dev-admin-key", alias="ADMIN_API_KEY")
    
    # Telegram Bot Settings
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    
    # Razorpay Settings
    razorpay_key_id: str = Field(default="", alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str = Field(default="", alias="RAZORPAY_KEY_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True

settings = Settings()
