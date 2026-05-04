import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.belgium_scraper import belgium_scraper
from ..services.slot_lifecycle_service import process_slots_lifecycle
from ..models.entities import User, AlertPreference, SlotPattern

async def check_and_alert_job(db: AsyncSession):
    """
    Consolidated job for automated scraping and change detection.
    """
    logging.info("Starting production-grade Belgium check...")
    
    # 1. Fetch from real scraper
    try:
        # Expand regions (Sprint 3.5 requirement)
        centers = ["London", "Manchester"]
        for center in centers:
            new_slots = await belgium_scraper.fetch_slots(center=center)
            
            # 2. Lifecycle & Change Detection
            if new_slots:
                await process_slots_lifecycle(db, "Belgium", center, new_slots)
            else:
                logging.info(f"No slots found for {center} in this poll.")
                
    except Exception as e:
        logging.error(f"Belgium Scraper failed: {e}")

    # 3. Predictive Context (for log/future scaling)
    current_hour = datetime.utcnow().hour
    # ... logic for patterns could be added here if needed for dynamic polling state ...

    logging.info("Finished Belgium check.")

async def is_peak_time(db: AsyncSession):
    """
    Checks if current time is within any corridor's peak window.
    """
    current_hour = datetime.utcnow().hour
    stmt = select(SlotPattern)
    res = await db.execute(stmt)
    patterns = res.scalars().all()
    
    for p in patterns:
        start_h = int(p.peak_start_time.split(':')[0])
        end_h = int(p.peak_end_time.split(':')[0])
        if start_h <= end_h:
            if start_h <= current_hour <= end_h: return True
        else:
            if current_hour >= start_h or current_hour <= end_h: return True
    return False
