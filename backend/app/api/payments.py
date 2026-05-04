import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from ..database.session import get_db
from ..models.entities import User, Payment, SubscriptionRecord
from ..services.payment_service import payment_service

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/create-order")
async def create_order(user_id: str, amount: int, db: AsyncSession = Depends(get_db)):
    """
    Creates a Razorpay order for a user.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Amount is in paisa (e.g. 99900 for 999 INR)
    order = payment_service.create_order(amount, f"sub_{user_id}")
    if not order:
        raise HTTPException(status_code=500, detail="Could not create payment order")
    
    # Save pending payment
    payment = Payment(
        user_id=user.id,
        amount=amount,
        status="pending",
        provider="razorpay",
        order_id=order['id']
    )
    db.add(payment)
    await db.commit()
    
    return order

@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handles Razorpay payment success webhooks.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    if not payment_service.verify_signature(body.decode(), signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    data = json.loads(body)
    event = data.get("event")
    
    if event == "payment.captured":
        payload = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payload.get("order_id")
        payment_id = payload.get("id")
        
        # 1. Update Payment Record
        stmt = select(Payment).where(Payment.order_id == order_id)
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()
        
        if payment:
            payment.status = "completed"
            payment.payment_id = payment_id
            
            # 2. Update User & Subscription
            user = await db.get(User, payment.user_id)
            if user:
                user.subscription_type = "premium"
                expiry = datetime.utcnow() + timedelta(days=30)
                user.subscription_expiry = expiry
                
                # Add Subscription Record
                sub = SubscriptionRecord(
                    user_id=user.id,
                    plan="premium",
                    end_date=expiry,
                    status="active"
                )
                db.add(sub)
                
            await db.commit()
            logging.info(f"Subscription activated for user {user.id}")
            
    return {"status": "ok"}
