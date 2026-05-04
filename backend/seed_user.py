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
        
        # We use the password provided by the user for the admin account
        admin_password = "vixa_admin_2026"
        
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="admin@vixaa.online",
                name="Admin User",
                telegram_chat_id="1746945796",
                password_hash=get_password_hash(admin_password),
                role="admin",
                subscription_type="premium",
                is_active=True
            )
            db.add(user)
            print(f"User created with admin password.")
        else:
            user.telegram_chat_id = "1746945796"
            user.role = "admin"
            user.password_hash = get_password_hash(admin_password)
            user.subscription_type = "premium"
            user.is_active = True
            print(f"User updated with admin password: {admin_password}")
            
        await db.commit()

if __name__ == "__main__":
    asyncio.run(seed_user())
