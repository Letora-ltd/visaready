from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from ..database.session import AsyncSessionLocal
from .jobs import check_and_alert_job, is_peak_time
from ..core.logging import logger

scheduler = AsyncIOScheduler()

# Global state to track last run for off-peak throttling
last_run_time = datetime.min

async def start_scheduler():
    async def smart_poll_job():
        global last_run_time
        now = datetime.utcnow()
        logger.debug("Starting smart poll job")
        
        try:
            async with AsyncSessionLocal() as db:
                peak = await is_peak_time(db)
                
                # Smart Polling Logic
                if peak:
                    await check_and_alert_job(db)
                    last_run_time = now
                else:
                    if now - last_run_time >= timedelta(minutes=5):
                        await check_and_alert_job(db)
                        last_run_time = now
        except Exception as e:
            logger.error(f"Error in smart_poll_job: {e}", exc_info=True)

    async def pattern_job():
        logger.info("Starting hourly pattern analysis job")
        try:
            async with AsyncSessionLocal() as db:
                from ..services.pattern_service import analyze_and_update_patterns
                await analyze_and_update_patterns(db)
                logger.info("Pattern analysis job completed successfully")
        except Exception as e:
            logger.error(f"Error in pattern_job: {e}", exc_info=True)

    # Check for slots every 30 seconds (Smart Polling will throttle inside)
    scheduler.add_job(
        smart_poll_job, 
        'interval', 
        seconds=30, 
        max_instances=1, 
        coalesce=True
    )
    
    async def subscription_cleanup_job():
        logger.info("Starting subscription cleanup job")
        try:
            async with AsyncSessionLocal() as db:
                from ..services.subscription_worker import cleanup_expired_subscriptions
                await cleanup_expired_subscriptions(db)
                logger.info("Subscription cleanup completed")
        except Exception as e:
            logger.error(f"Error in subscription_cleanup_job: {e}", exc_info=True)

    # Analyze patterns every hour
    scheduler.add_job(
        pattern_job,
        'interval',
        hours=1,
        max_instances=1,
        coalesce=True
    )

    # Cleanup expired subscriptions every 12 hours
    scheduler.add_job(
        subscription_cleanup_job,
        'interval',
        hours=12,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
