import logging
import sys
from logging.handlers import RotatingFileHandler
from .config import settings

def setup_logging():
    # Structured logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "vixa_production.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "formatter": "default",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"]
        }
    }

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("vixa_production.log", maxBytes=10485760, backupCount=5)
        ]
    )

    # Specific loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger("vixaa")
