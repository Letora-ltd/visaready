import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from ..database.session import AsyncSessionLocal
from ..models.entities import User, UserDailyStats, AlertPreference
from ..services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

async def run_daily_summaries():
    """
    Sends a recap of today's visa activity to all active users (Sprint 4).
    Typically runs once per evening.
    """
    logger.info("📊 Starting Daily Summary Dispatch...")
    
    async with AsyncSessionLocal() as db:
        # Get all users with alerts enabled
        stmt = select(User).where(User.alerts_enabled == True)
        res = await db.execute(stmt)
        users = res.scalars().all()
        
        today = datetime.now().date()
        
        sent_count = 0
        for user in users:
            if not user.telegram_chat_id: continue
            
            # 1. Get Stats
            stats_stmt = select(UserDailyStats).where(
                and_(UserDailyStats.user_id == user.id, UserDailyStats.date == today)
            )
            stats = (await db.execute(stats_stmt)).scalars().first()
            
            if not stats or stats.slots_found == 0:
                continue
                
            # 2. Get Insights (Peak Hour)
            pref_stmt = select(AlertPreference).where(AlertPreference.user_id == user.id).limit(1)
            pref = (await db.execute(pref_stmt)).scalars().first()
            
            peak_text = ""
            if pref:
                from ..core.intelligence import intelligence_engine
                best_h = None
                max_s = 0
                for h in range(24):
                    s = await intelligence_engine.get_center_score(pref.center, h)
                    if s > max_s:
                        max_s = s
                        best_h = h
                if best_h is not None:
                    peak_text = f"🔥 <b>Peak time ({pref.center}):</b> {best_h:02}:00 - {best_h+1:02}:00\n"

            # 3. Format Summary
            missed = stats.slots_found - stats.alerts_sent
            
            summary = (
                f"📊 <b>Daily Visa Summary</b>\n\n"
                f"Slots detected today: <b>{stats.slots_found}</b>\n"
                f"Alerts sent to you: <b>{stats.alerts_sent}</b>\n"
            )
            
            if missed > 0:
                summary += f"⚠️ <b>Missed opportunities: {missed}</b>\n"
                summary += "<i>(Free users experience a 3-minute delay)</i>\n\n"
            else:
                summary += "✅ <b>You caught every slot!</b>\n\n"
                
            summary += peak_text
            summary += "\n🚀 /upgrade for instant priority alerts."
            
            try:
                await telegram_service.send_message(user.telegram_chat_id, summary)
                sent_count += 1
                # Rate limit
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Failed to send summary to {user.id}: {e}")

    logger.info(f"📊 Daily Summary Complete. Sent to {sent_count} users.")

async def summary_scheduler():
    """Background task to trigger summaries at 21:00 every day."""
    while True:
        now = datetime.now()
        # Trigger at 21:00 (9 PM)
        if now.hour == 21 and now.minute == 0:
            await run_daily_summaries()
            await asyncio.sleep(60) # Wait for minute to pass
        await asyncio.sleep(30)
