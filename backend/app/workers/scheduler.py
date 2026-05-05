from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, time
from ..database.session import AsyncSessionLocal
from .jobs import check_and_alert_job
from ..core.intelligence import intelligence_engine, MonitoringMode
from ..core.health import health_monitor, SystemState
from ..core.metrics import metrics
from ..core.queue import slot_queue
from ..core.logging import logger
from .db_worker import start_db_worker
from ..services.session_pool import session_pool
import logging

scheduler = AsyncIOScheduler()

# Center-Level tracking of last scan
last_scan_times = {}

async def smart_poll_job():
    """
    Intelligent Center-Level Dispatcher (Sprint 6).
    Evaluates each center independently based on its Mode and Heat Score.
    """
    global last_scan_times
    now = datetime.now()
    current_hour = now.hour
    
    # Target Centers (This could come from DB in Sprint 7)
    centers = ["London", "Manchester"]
    
    due_centers = []
    
    for center in centers:
        # 1. Get Center-Specific Mode
        mode = await intelligence_engine.get_center_mode(center)
        mode_interval = intelligence_engine.get_interval(mode)
        
        # 2. Get Heat Score (Weighted Patterns)
        heat_score = await intelligence_engine.get_center_score(center, current_hour)
        
        # 3. Dynamic Interval Logic
        final_interval = mode_interval
        
        # If heat is high (> 2.0 confirmed events), tighten NORMAL interval
        if mode == MonitoringMode.NORMAL and heat_score > 2.0:
            final_interval = min(final_interval, 2)
            logger.debug(f"🔥 [{center}] High Heat detected. Tightening interval.")
        
        # 4. Fail-Safe Override (Sprint 7)
        health_state = await health_monitor.get_state()
        if health_state == SystemState.DEGRADED:
            final_interval = max(final_interval, 5) 
            logger.warning(f"⚠️ HEALTH OVERRIDE: System DEGRADED. Throttling {center} to {final_interval}m")
        elif health_state == SystemState.CRITICAL:
            final_interval = max(final_interval, 15)
            logger.error(f"🚨 HEALTH OVERRIDE: System CRITICAL. Throttling {center} to {final_interval}m")

        logger.info(f"🧠 Intelligence: Center={center}, Mode={mode.value}, Health={health_state.value}, Interval={final_interval}m")

        # Check if scan is due
        last_run = last_scan_times.get(center, datetime.min)
        if now - last_run >= timedelta(minutes=final_interval):
            due_centers.append(center)
            last_scan_times[center] = now
            logger.info(f"⏰ Scheduler: [{center}] is DUE (Mode: {mode.value}, Interval: {final_interval}m, Heat: {heat_score:.1f})")

    # Dispatch only due centers
    if due_centers:
        async with AsyncSessionLocal() as db:
            await check_and_alert_job(db, centers=due_centers)

async def summary_job():
    """Periodic Operator Summary (Sprint 7)."""
    state = await health_monitor.get_state()
    report = metrics.get_report()
    logger.info(f"""
📋 --- SYSTEM HEALTH SUMMARY ---
State: {state.value}
Success Rate: {health_monitor.get_success_rate()*100:.1f}%
Total Runs: {report['runs_started']}
Avg Duration: {report['avg_success_duration']}s
Queue Size: {slot_queue.qsize()}
-------------------------------
""")

async def start_scheduler():
    # 1. Start the DB Background Worker
    await start_db_worker()
    
    # 2. Initialize the Intelligence Engine (Load patterns from DB)
    await intelligence_engine.initialize()
    
    # 3. Initialize the Browser Session Pool
    await session_pool.initialize()
    
    # 4. Schedule the Pulse (Every 1 minute)
    scheduler.add_job(
        smart_poll_job, 
        'interval', 
        minutes=1, 
        max_instances=1, 
        coalesce=True
    )
    
    # Operator Summary every 5 minutes
    scheduler.add_job(
        summary_job,
        'interval',
        minutes=5,
        max_instances=1,
        coalesce=True
    )
    
    scheduler.start()
    logger.info("📅 APScheduler started with Center-Level Targeting.")
