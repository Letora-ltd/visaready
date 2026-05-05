import asyncio
import os
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.entities import User

async def get_tg_id():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_chat_id != None))
        user = result.scalars().first()
        if user:
            print(f"FOUND_TG_ID: {user.telegram_chat_id}")
        else:
            print("NO_TG_ID_FOUND")

if __name__ == "__main__":
    asyncio.run(get_tg_id())
