import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.alert_dispatcher import alert_dispatcher
from app.database.session import AsyncSessionLocal
from app.models.entities import User, UserDailyStats
from sqlalchemy import select

async def test_triggers():
    print("=== TESTING SMART CONVERSION TRIGGERS (SPRINT G2) ===")
    chat_id = "7499696345"
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user:
            print("❌ User not found.")
            return

        # Reset Stats for test
        today = datetime.now().date()
        from sqlalchemy import delete
        await db.execute(delete(UserDailyStats).where(UserDailyStats.user_id == user.id))
        await db.commit()

        # 1. Test Trigger: Missed Slots (Loss Aversion)
        print("\n1. Testing 'Missed Slots' Trigger (Simulating 3 missed)...")
        # Pre-populate missed slots
        await alert_dispatcher._update_stats(user.id, 3, 0, db) 
        
        # Dispatch a new alert - should trigger prompt
        test_slots = [{"slot_date": datetime.now() + timedelta(days=5), "slot_time": "10:00"}]
        await alert_dispatcher.dispatch(db, "Belgium", "London", test_slots)
        
        await db.refresh(user)
        # Check prompts_shown in stats
        stats = (await db.execute(select(UserDailyStats).where(UserDailyStats.user_id == user.id))).scalars().first()
        print(f"✅ Prompts shown today: {stats.prompts_shown}")
        if stats.prompts_shown == 1:
            print("🎯 SUCCESS: Missed slots trigger fired!")

        # 2. Test Throttling (Trigger second prompt)
        print("\n2. Testing Throttling (Firing second prompt)...")
        await alert_dispatcher.dispatch(db, "Belgium", "Manchester", test_slots)
        await db.refresh(stats)
        print(f"✅ Prompts shown today: {stats.prompts_shown}")
        
        # 3. Test Throttling Limit (Try to fire third - should be blocked)
        print("\n3. Testing Throttling Limit (Max 2)...")
        await alert_dispatcher.dispatch(db, "Belgium", "Edinburgh", test_slots)
        await db.refresh(stats)
        print(f"✅ Prompts shown today: {stats.prompts_shown} (Should still be 2)")
        if stats.prompts_shown == 2:
            print("🛡️ SUCCESS: Throttling blocked the third prompt!")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_triggers())
