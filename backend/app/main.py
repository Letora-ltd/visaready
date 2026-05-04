from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
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

# Serve Frontend (Must be last to avoid shadowing API)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
