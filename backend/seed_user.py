import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.entities import User
from app.core.security import get_password_hash

async def seed_user():
    async with AsyncSessionLocal() as db:
        # Check if user exists
        stmt = select(User).where(User.email == "admin@vixaa.online")
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="admin@vixaa.online",
                name="Admin User",
                telegram_chat_id="1746945796",
                password_hash=get_password_hash("khajaa250419"),
                role="admin",
                subscription_type="premium",
                is_active=True
            )
            db.add(user)
            print(f"User created with Telegram ID: 1746945796")
        else:
            user.telegram_chat_id = "1746945796"
            user.role = "admin"
            user.password_hash = get_password_hash("khajaa250419")
            user.subscription_type = "premium"
            user.is_active = True
            print(f"User updated with new password hash.")
            
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_user())
