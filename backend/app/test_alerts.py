import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.alert_dispatcher import alert_dispatcher
from app.database.session import AsyncSessionLocal
from app.models.entities import User, AlertPreference, ActivityLog
from sqlalchemy import select

async def test_alerts():
    print("=== TESTING ALERT DISPATCHER (SPRINT 2) ===")
    chat_id = "7499696345"
    
    async with AsyncSessionLocal() as db:
        # 1. Setup User for London (Belgium)
        print("\n1. Ensuring user has preferences for London...")
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            print("❌ User not found.")
            return
            
        # Ensure preference exists
        pref_res = await db.execute(select(AlertPreference).where(
            AlertPreference.user_id == user.id,
            AlertPreference.center == "London"
        ))
        if not pref_res.scalars().first():
            db.add(AlertPreference(user_id=user.id, country="Belgium", center="London"))
            await db.commit()
            print("✅ Added preference for London.")

        # 2. Test Dispatch (Free User)
        user.subscription_type = "free"
        user.alerts_enabled = True
        await db.commit()
        
        test_slots = [
            {"slot_date": datetime.now() + timedelta(days=10), "slot_time": "09:00"},
            {"slot_date": datetime.now() + timedelta(days=12), "slot_time": "11:30"}
        ]
        
        print("\n2. Dispatching alert for FREE user (should be delayed)...")
        await alert_dispatcher.dispatch(db, "Belgium", "London", test_slots)
        
        # 3. Test Dispatch (Premium User)
        print("\n3. Dispatching alert for PREMIUM user (should be instant)...")
        user.subscription_type = "premium"
        user.subscription_expiry = datetime.now() + timedelta(days=30)
        await db.commit()
        
        # Change center to Manchester to avoid anti-spam for a second
        await alert_dispatcher.dispatch(db, "Belgium", "London", test_slots)

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_alerts())
