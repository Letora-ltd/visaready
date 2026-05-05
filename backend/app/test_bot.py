import asyncio
import os
import sys

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.telegram_service import telegram_service
from app.database.session import AsyncSessionLocal
from app.models.entities import User, AlertPreference
from sqlalchemy import select

async def test_bot():
    print("=== TESTING TELEGRAM BOT LOGIC (SPRINT 1) ===")
    
    # Mock update for /start
    update = {
        "message": {
            "chat": {"id": 7499696345},
            "text": "/start"
        }
    }
    
    async with AsyncSessionLocal() as db:
        print("\n1. Testing /start...")
        await telegram_service.handle_webhook(update, db)
        
        # Verify user creation
        result = await db.execute(select(User).where(User.telegram_chat_id == "7499696345"))
        user = result.scalars().first()
        if user:
            print(f"✅ User created: {user.email}")
        else:
            print("❌ User NOT created.")

        print("\n2. Testing /track London...")
        await telegram_service.process_text_selection("7499696345", "/track London", db)
        
        # Verify preference
        pref_result = await db.execute(select(AlertPreference).where(AlertPreference.user_id == user.id))
        prefs = pref_result.scalars().all()
        if prefs:
            print(f"✅ Preferences found: {[(p.center, p.country) for p in prefs]}")
        else:
            print("❌ Preferences NOT found.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_bot())
