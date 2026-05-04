import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.entities import User

async def check_user():
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.email == "admin@vixa.online")
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            print(f"User admin@vixa.online found. Role: {user.role}, Is Active: {user.is_active}")
        else:
            print("User admin@vixa.online NOT found.")

        stmt2 = select(User).where(User.email == "admin@vixaa.online")
        res2 = await db.execute(stmt2)
        user2 = res2.scalar_one_or_none()
        if user2:
            print(f"User admin@vixaa.online found. Role: {user2.role}, Is Active: {user2.is_active}")
        else:
            print("User admin@vixaa.online NOT found.")

if __name__ == "__main__":
    asyncio.run(check_user())
