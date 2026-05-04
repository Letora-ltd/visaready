import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.logging import setup_logging, logger
from .api import visa, admin, auth, endpoints, vixaa, admin_france, payments, bot, debug
from .database.init_db import init_db
from .workers.scheduler import start_scheduler

# Initialize logging
setup_logging()

app = FastAPI(title="Vixa Visa Intelligence API")
app.include_router(debug.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Our engineers have been notified."},
    )

# Rate Limiting State
rate_limit_store = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    path = request.url.path
    
    # Rate limit sensitive routes: signup, login, reports
    if any(p in path for p in ["/register", "/login", "/reports/submit"]):
        now = datetime.now()
        key = f"{client_ip}:{path}"
        
        if key in rate_limit_store:
            last_request_time, count = rate_limit_store[key]
            if now - last_request_time < timedelta(minutes=1):
                if count >= 10: # Max 10 requests per minute
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please try again in a minute."}
                    )
                rate_limit_store[key] = (last_request_time, count + 1)
            else:
                rate_limit_store[key] = (now, 1)
        else:
            rate_limit_store[key] = (now, 1)

    response = await call_next(request)
    return response

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
app.include_router(vixaa.router)
app.include_router(admin_france.router)
app.include_router(payments.router)
app.include_router(bot.router)

@app.get('/api/health')
def health():
    return {"success": True, "data": {"status": "ok"}}

@app.on_event("startup")
async def on_startup():
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Only start scheduler if not on Vercel
    if not os.environ.get("VERCEL"):
        try:
            await start_scheduler()
        except Exception as e:
            logger.error(f"Scheduler failed to start: {e}")
