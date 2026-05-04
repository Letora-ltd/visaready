import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api import visa, admin, auth, endpoints
from .database.init_db import init_db
from .workers.scheduler import start_scheduler

app = FastAPI(title="VisaReady API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(visa.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(endpoints.router)

@app.get('/health')
def health():
    return {"success": True, "data": {"status": "ok"}}


@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
    
    # Only start scheduler if not on Vercel (ephemeral environment)
    if not os.environ.get("VERCEL"):
        try:
            start_scheduler()
        except Exception as e:
            logging.error(f"Scheduler failed to start: {e}")
