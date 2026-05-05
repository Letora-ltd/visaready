import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.alert_dispatcher import alert_dispatcher
from app.database.session import AsyncSessionLocal
from app.models.entities import User, AlertPreference
from sqlalchemy import select

async def test_downgrade():
    print("=== TESTING AUTO-DOWNGRADE & GRACE PERIOD (SPRINT 3.5) ===")
    chat_id = "7499696345"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            print("❌ User not found.")
            return

        # 1. Test Grace Period (Expired 1 day ago)
        print("\n1. Testing Grace Period (Expired 1 day ago)...")
        user.subscription_type = "premium"
        user.subscription_expiry = datetime.now() - timedelta(days=1)
        await db.commit()
        
        test_slots = [{"slot_date": datetime.now() + timedelta(days=5), "slot_time": "10:00"}]
        await alert_dispatcher.dispatch(db, "Belgium", "London", test_slots)
        
        await db.refresh(user)
        print(f"✅ User Plan (should be premium during grace): {user.subscription_type}")

        # 2. Test Auto-Downgrade (Expired 3 days ago)
        print("\n2. Testing Auto-Downgrade (Expired 3 days ago)...")
        user.subscription_expiry = datetime.now() - timedelta(days=3)
        await db.commit()
        
        # New center to avoid dedupe
        await alert_dispatcher.dispatch(db, "Belgium", "Manchester", test_slots)
        
        await db.refresh(user)
        print(f"✅ User Plan (should be free after grace): {user.subscription_type}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_downgrade())
