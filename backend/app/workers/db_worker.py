import asyncio
import logging
import time
from datetime import datetime
from ..core.queue import slot_queue
from ..services.slot_lifecycle_service import process_slots_lifecycle
from ..database.session import AsyncSessionLocal
from ..core.health import health_monitor

logger = logging.getLogger(__name__)

async def db_writer_worker():
    """
    Continuous background worker that consumes the slot queue and writes to DB safely.
    Implements retry logic with exponential backoff.
    """
    logger.info("🚀 DB Writer Worker started. Waiting for queue data...")
    
    while True:
        # Get item from queue
        item = await slot_queue.get()
        
        try:
            country = item.get("country", "Belgium")
            center = item.get("center", "London")
            slots = item.get("slots", [])
            timestamp = item.get("timestamp", datetime.now())
            
            logger.info(f"📥 Worker consuming data for {country}/{center} ({len(slots)} slots)")
            
            # Retry logic
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    async with AsyncSessionLocal() as db:
                        # This handles: Snapshot -> Slot Update -> Change Detection -> Alerts
                        await process_slots_lifecycle(db, country, center, slots)
                        success = True
                        await health_monitor.report_db_event(success=True)
                        logger.info(f"✅ Successfully wrote {country}/{center} to DB.")
                except Exception as db_err:
                    retry_count += 1
                    await health_monitor.report_db_event(success=False)
                    wait_time = 2 ** retry_count # Exponential backoff: 2, 4, 8s
                    logger.error(f"❌ DB Write Error (Attempt {retry_count}/{max_retries}): {db_err}")
                    if retry_count < max_retries:
                        logger.info(f"⏳ Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
            
            if not success:
                logger.error(f"💀 CRITICAL: Failed to write data for {country}/{center} after {max_retries} attempts. Data lost for this cycle.")
                
        except Exception as e:
            logger.error(f"Unexpected error in DB Writer Worker: {e}")
        finally:
            # Mark task as done
            slot_queue.task_done()
            logger.info(f"📊 Queue Size: {slot_queue.qsize()}")

async def start_db_worker():
    """
    Helper to start the worker as a background task.
    """
    asyncio.create_task(db_writer_worker())
