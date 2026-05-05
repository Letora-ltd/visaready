import asyncio
import sys
import os
import json
from unittest.mock import MagicMock

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock stripe before importing payment_service
import stripe
stripe.checkout = MagicMock()
stripe.checkout.Session = MagicMock()
stripe.checkout.Session.create = MagicMock(return_value=MagicMock(url="https://stripe.com/test_checkout"))
stripe.Webhook = MagicMock()
stripe.Webhook.construct_event = MagicMock()

from app.services.payment_service import payment_service
from app.database.session import AsyncSessionLocal
from app.models.entities import User

async def test_payments():
    print("=== TESTING PAYMENT FLOW (SPRINT 3) ===")
    chat_id = "7499696345"
    
    async with AsyncSessionLocal() as db:
        # 1. Test Create Checkout
        print("\n1. Testing Create Checkout...")
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            print("❌ User not found.")
            return
            
        url = await payment_service.create_checkout_session(str(user.id), user.email)
        print(f"✅ Generated Checkout URL: {url}")

        # 2. Test Webhook Mock (Activation)
        print("\n2. Testing Webhook Activation...")
        # Mocking the event object
        stripe.Webhook.construct_event.return_value = {
            'type': 'checkout.session.completed',
            'data': {'object': {'client_reference_id': str(user.id)}}
        }
        
        await payment_service.handle_webhook(b"payload", "sig", db)
        
        # Verify Activation
        # Re-fetch user
        await db.refresh(user)
        print(f"✅ User Plan after webhook: {user.subscription_type}")
        if user.subscription_type == 'premium':
            print("🏆 SUCCESS: Premium activated via webhook!")

    print("\n=== TEST COMPLETE ===")

from sqlalchemy import select

if __name__ == "__main__":
    asyncio.run(test_payments())
