import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Global In-Memory Queue for Slot Results
# This decouples the browser scraper (heavy) from the database writes (latent/fragile)
slot_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=100)

def get_slot_queue() -> asyncio.Queue:
    return slot_queue

async def push_to_queue(data: Dict[str, Any]):
    """
    Safely pushes data into the queue.
    """
    try:
        if slot_queue.full():
            logger.warning("Slot queue is FULL. Dropping oldest data to make room.")
            slot_queue.get_nowait()
            
        await slot_queue.put(data)
        logger.info(f"Data pushed to queue. Current size: {slot_queue.qsize()}")
    except Exception as e:
        logger.error(f"Failed to push to queue: {e}")
