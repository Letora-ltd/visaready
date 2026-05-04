from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import User, SubscriptionRecord
from ..core.logging import logger

async def cleanup_expired_subscriptions(db: AsyncSession):
    """
    Finds all expired premium users and reverts them to the free tier.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Update User records
    stmt = select(User).where(
        and_(
            User.subscription_type == "premium",
            User.subscription_expiry < now
        )
    )
    res = await db.execute(stmt)
    expired_users = res.scalars().all()
    
    for user in expired_users:
        logger.info(f"Subscription expired for user {user.id}. Reverting to free.")
        user.subscription_type = "free"
        
        # 2. Update Subscription Records
        sub_stmt = select(SubscriptionRecord).where(
            and_(
                SubscriptionRecord.user_id == user.id,
                SubscriptionRecord.status == "active"
            )
        )
        sub_res = await db.execute(sub_stmt)
        active_sub = sub_res.scalar_one_or_none()
        if active_sub:
            active_sub.status = "expired"
            
    await db.commit()
