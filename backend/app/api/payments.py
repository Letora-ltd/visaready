from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.session import AsyncSessionLocal
from ..services.payment_service import payment_service
import logging

router = APIRouter(prefix="/api/payments", tags=["payments"])
logger = logging.getLogger(__name__)

@router.post("/create-checkout")
async def create_checkout(user_id: str, email: str):
    """Generates a Stripe Checkout URL for the user."""
    try:
        url = await payment_service.create_checkout_session(user_id, email)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Receives and validates Stripe events."""
    payload = await request.body()
    
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature")

    async with AsyncSessionLocal() as db:
        try:
            await payment_service.handle_webhook(payload, stripe_signature, db)
            return {"status": "success"}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except Exception as e:
            logger.error(f"Webhook Error: {e}")
            raise HTTPException(status_code=400, detail="Webhook Error")
