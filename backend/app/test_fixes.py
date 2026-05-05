import asyncio
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.telegram_service import telegram_service
from app.database.session import AsyncSessionLocal
from app.models.entities import User, AlertPreference
from sqlalchemy import select

async def test_fixes():
    print("=== TESTING QUICK FIXES (SPRINT 1.5) ===")
    chat_id = "7499696345"
    
    async with AsyncSessionLocal() as db:
        # 1. Test /start Defaults
        print("\n1. Testing /start defaults...")
        await telegram_service._handle_start(chat_id, db)
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        print(f"User Plan: {user.subscription_type}, Alerts Enabled: {user.alerts_enabled}")

        # 2. Test Normalization & Validation
        print("\n2. Testing normalization ('/track LoNdOn ')...")
        await telegram_service.process_text_selection(chat_id, "/track LoNdOn ", db)
        
        # 3. Test Duplicates
        print("\n3. Testing duplicates...")
        await telegram_service.process_text_selection(chat_id, "/track london", db)
        
        # 4. Test Validation (Invalid center)
        print("\n4. Testing invalid center...")
        await telegram_service.process_text_selection(chat_id, "/track paris", db)
        
        # 5. Test /untrack
        print("\n5. Testing /untrack...")
        await telegram_service.process_text_selection(chat_id, "/untrack london", db)

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_fixes())
