import logging
import sys
from logging.handlers import RotatingFileHandler
from .config import settings

import os

def setup_logging():
    # Detect Vercel environment
    is_vercel = os.environ.get("VERCEL") == "1"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if not is_vercel:
        try:
            file_handler = RotatingFileHandler("vixa_production.log", maxBytes=10485760, backupCount=5)
            handlers.append(file_handler)
        except Exception as e:
            print(f"Failed to initialize file logging: {e}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )

    # Specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger("vixaa")
