import asyncio
from ..database.session import AsyncSessionLocal
from ..models.entities import User
from ..core.security import get_password_hash
from sqlalchemy import select

async def seed_admin():
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin exists
            admin_email = "admin@vixa.online"
            existing = (await db.execute(select(User).where(User.email == admin_email))).scalars().first()
            if existing:
                print(f"Admin {admin_email} already exists.")
                return
            
            admin = User(
                email=admin_email,
                name="Vixa Admin",
                password_hash=get_password_hash("vixa_admin_2026"),
                role='admin',
                is_active=True,
                subscription_type='premium' # Admins get premium
            )
            db.add(admin)
            await db.commit()
            print(f"Admin {admin_email} created successfully.")
        except Exception as e:
            print(f"Error seeding admin: {e}")

if __name__ == "__main__":
    asyncio.run(seed_admin())
