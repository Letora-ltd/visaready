from .belgium_scraper import belgium_scraper
import logging

logger = logging.getLogger(__name__)

async def fetch_belgium_slots():
    """
    Fetches real visa slots for Belgium using the BelgiumScraper.
    Replaces the previous mock implementation.
    """
    logger.info("Triggering real Belgium slot fetch via checker service...")
    try:
        # For now, we default to 'brussels' or 'London' as a test center
        slots = await belgium_scraper.fetch_slots(center="London")
        
        # Normalize to the format expected by the caller if necessary
        # The caller expects a list of dicts with:
        # {country, center, visa_type, slot_date, slot_time}
        return slots
    except Exception as e:
        logger.error(f"Failed to fetch real Belgium slots: {e}")
        return []
