import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict
from ..services.belgium_browser_scraper import belgium_browser_scraper
from ..core.queue import push_to_queue, slot_queue
from ..services.session_pool import session_pool
from ..core.metrics import metrics
from ..core.intelligence import intelligence_engine
from ..core.health import health_monitor, SystemState

logger = logging.getLogger(__name__)

# Concurrency Control (Sprint 3)
MAX_WORKERS = 2
worker_semaphore = asyncio.Semaphore(MAX_WORKERS)

async def check_and_alert_job(db=None, centers: List[str] = None):
    """
    Main job triggered by the scheduler. 
    Now acts as a dispatcher for the parallel worker pool.
    """
    if not centers:
        centers = ["London"]
    
    tasks = []
    for center in centers:
        # Launch parallel tasks (Dispatcher doesn't wait for completion)
        tasks.append(run_scrape_task(center))
    
    await asyncio.gather(*tasks)

async def run_scrape_task(center: str):
    """
    Individual scraping task that runs within the semaphore limit.
    Integrates session pooling, jitter, and metrics.
    """
    async with worker_semaphore:
        # 0. Fail-Safe Check (Sprint 7)
        state = await health_monitor.get_state()
        if state == SystemState.CRITICAL:
            logger.warning("🚨 FAIL-SAFE: System in CRITICAL state. Limiting workers and increasing delay.")
            await asyncio.sleep(60) # Extra safety delay

        # 1. Backpressure Check
        q_size = slot_queue.qsize()
        if q_size > 50:
            logger.warning(f"⚠️ Backpressure: Queue size ({q_size}) exceeds threshold. Skipping task.")
            return

        # 2. Acquire Pooled Session
        session = await session_pool.acquire()
        if not session:
            logger.warning("❌ No available sessions in pool. All workers busy or sessions invalid.")
            return

        session_id = session["id"]
        logger.info(f"🚀 Starting parallel task for {center} using Session {session_id}")
        
        metrics.log_start()
        start_time = time.time()
        
        try:
            # 3. Random Jitter (Anti-blocking)
            jitter = random.uniform(5, 20)
            logger.info(f"⏳ [{session_id}] Adding jitter: {jitter:.1f}s")
            await asyncio.sleep(jitter)
            
            # 4. Execute Flow (VOW -> TLS -> Capture)
            # We wrap in a timeout to prevent hanging tasks
            try:
                new_slots = await asyncio.wait_for(
                    belgium_browser_scraper.fetch_slots_with_vow(center=center, session_info=session),
                    timeout=150.0 # Total task timeout
                )
                
                # 5. Handle Results
                if new_slots:
                    logger.info(f"✅ [{session_id}] Task success: Found {len(new_slots)} slots.")
                    
                    # Signal Intelligence (Confidence Filter + Activity Memory)
                    await intelligence_engine.report_signal("slot_detected", {
                        "count": len(new_slots), 
                        "center": center,
                        "session_id": session_id
                    })
                    await session_pool.report_health(session_id, success=True)
                    await health_monitor.report_run(success=True)
                    
                    await push_to_queue({
                        "country": "Belgium",
                        "center": center,
                        "slots": new_slots,
                        "timestamp": datetime.now()
                    })
                    metrics.log_run(success=True, duration=time.time() - start_time)
                    
                    # FAST RE-CHECK LOGIC (Sprint 4)
                    # Trigger another check in 45 seconds to capture burst releases
                    asyncio.create_task(delayed_recheck(center))

                else:
                    logger.info(f"ℹ️ [{session_id}] Task completed: No slots found.")
                    await intelligence_engine.report_signal("success") 
                    await session_pool.report_health(session_id, success=True)
                    await health_monitor.report_run(success=True)
                    metrics.log_run(success=False, duration=time.time() - start_time)

            except asyncio.TimeoutError:
                logger.error(f"⌛ [{session_id}] Task TIMEOUT after 150s.")
                await intelligence_engine.report_signal("failure")
                await session_pool.report_health(session_id, success=False)
                await health_monitor.report_run(success=False)
                metrics.log_run(success=False, duration=time.time() - start_time)

        except Exception as e:
            logger.error(f"💥 [{session_id}] Task FATAL ERROR: {e}")
            await intelligence_engine.report_signal("failure")
            await session_pool.report_health(session_id, success=False)
            await health_monitor.report_run(success=False)
            metrics.log_run(success=False, duration=time.time() - start_time)
        finally:
            # 6. Return Session to Pool
            await session_pool.release(session_id)
            logger.info(f"📥 [{session_id}] Task finished. Session released. Metrics: {metrics.get_report()}")

def is_peak_time():
    """Legacy helper for simple window logic (unused by smart scheduler but kept for compat)"""
    now = datetime.now().time()
    return (now >= datetime.strptime("09:00", "%H:%M").time() and now <= datetime.strptime("11:00", "%H:%M").time()) or \
           (now >= datetime.strptime("14:00", "%H:%M").time() and now <= datetime.strptime("16:00", "%H:%M").time())

async def delayed_recheck(center: str):
    """
    Triggers an immediate follow-up scan after a short delay (Sprint 4).
    Captures slots that are released in waves.
    """
    wait_time = random.randint(30, 60)
    logger.info(f"🔄 Fast Re-check scheduled for {center} in {wait_time}s")
    await asyncio.sleep(wait_time)
    await run_scrape_task(center)
