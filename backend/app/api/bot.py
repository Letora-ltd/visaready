from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.session import AsyncSessionLocal
from ..services.telegram_service import telegram_service
import logging

# Set prefix to /api/telegram to match user request
router = APIRouter(prefix="/api/telegram", tags=["telegram-bot"])
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint for Telegram webhook updates.
    """
    try:
        update = await request.json()
        logger.info(f"Incoming Telegram Update: {update}")
        
        async with AsyncSessionLocal() as db:
            # 1. Standard command processing
            await telegram_service.handle_webhook(update, db)
            
            # 2. Text processing (e.g. /track London)
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"]
                chat_id = str(update["message"]["chat"]["id"])
                if text.startswith("/track"):
                    await telegram_service.process_text_selection(chat_id, text, db)
                    
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/status")
async def bot_status():
    """Simple health check for the bot token."""
    return {
        "bot_initialized": telegram_service.token is not None,
        "token_preview": f"{telegram_service.token[:8]}..." if telegram_service.token else "None"
    }
