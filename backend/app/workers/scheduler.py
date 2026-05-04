from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from ..database.session import AsyncSessionLocal
from .jobs import check_and_alert_job, is_peak_time

scheduler = AsyncIOScheduler()

# Global state to track last run for off-peak throttling
last_run_time = datetime.min

async def start_scheduler():
    async def smart_poll_job():
        global last_run_time
        now = datetime.utcnow()
        
        async with AsyncSessionLocal() as db:
            peak = await is_peak_time(db)
            
            # Smart Polling Logic
            # Peak: run every 30-60s (job runs every 30s)
            # Off-Peak: run every 3-5 mins
            if peak:
                # Run every time (every 30s)
                await check_and_alert_job(db)
                last_run_time = now
            else:
                # Only run if 5 minutes have passed since last run
                if now - last_run_time >= timedelta(minutes=5):
                    await check_and_alert_job(db)
                    last_run_time = now
                else:
                    pass # Skip poll for off-peak throttling

    async def pattern_job():
        async with AsyncSessionLocal() as db:
            from ..services.pattern_service import analyze_and_update_patterns
            await analyze_and_update_patterns(db)

    # Check for slots every 30 seconds (Smart Polling will throttle inside)
    scheduler.add_job(
        smart_poll_job, 
        'interval', 
        seconds=30, 
        max_instances=1, 
        coalesce=True
    )
    
    # Analyze patterns every hour
    scheduler.add_job(
        pattern_job,
        'interval',
        hours=1,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
