import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import User, AlertPreference, ActivityLog, UserDailyStats, ConversionLog
from ..services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

class AlertDispatcher:
    """
    Hardened Alert Delivery Engine (Refined).
    Handles grouping, flood control, and rate-limiting (Sprint 2.5).
    """
    def __init__(self):
        # Anti-spam: {user_id: {dedupe_key}}
        self.sent_alerts_cache: Dict[str, Set[str]] = {} 
        self.cache_lock = asyncio.Lock()
        
        # Async Flood Control (Sprint 2.5)
        self.telegram_semaphore = asyncio.Semaphore(20)

    async def dispatch(self, db: AsyncSession, country: str, center: str, slots: List[Dict]):
        """
        Dispatches grouped alerts with rate-limiting.
        """
        if not slots:
            return

        # 1. Get Intelligence Data (Confidence Score)
        confidence = 0.8 
        try:
            stmt = select(ActivityLog).where(ActivityLog.center == center).order_by(ActivityLog.timestamp.desc()).limit(1)
            result = await db.execute(stmt)
            latest_log = result.scalars().first()
            if latest_log:
                confidence = latest_log.confidence
        except Exception as e:
            logger.error(f"Error fetching confidence: {e}")

        # 2. Fetch Targeted Users
        user_stmt = select(User).join(AlertPreference).where(
            and_(
                AlertPreference.country == country,
                AlertPreference.center == center,
                User.telegram_chat_id != None,
                User.alerts_enabled == True
            )
        )
        res = await db.execute(user_stmt)
        users = res.scalars().all()
        
        if not users:
            return

        # 3. Filter New Slots vs Sent
        sent_count = 0
        skipped_duplicates = 0
        
        for user in users:
            chat_id = user.telegram_chat_id
            
            # Determine which slots are NEW for THIS user
            new_for_user = []
            async with self.cache_lock:
                if chat_id not in self.sent_alerts_cache:
                    self.sent_alerts_cache[chat_id] = set()
                
                user_cache = self.sent_alerts_cache[chat_id]
                
                for s in slots:
                    dedupe_key = f"{center}:{s['slot_date'].strftime('%Y-%m-%d')}:{s['slot_time']}"
                    if dedupe_key not in user_cache:
                        new_for_user.append(s)
                        user_cache.add(dedupe_key)
                        
                # Limit cache to 500 unique slot keys per user to prevent memory bloat
                if len(user_cache) > 500:
                    # Clear older entries (simplified: just clear all if exceeded)
                    self.sent_alerts_cache[chat_id] = set(list(user_cache)[-200:])

            if not new_for_user:
                skipped_duplicates += 1
                continue

            # 4. Premium Expiry & Grace Period Check (Sprint 3.5)
            now_time = datetime.now()
            is_premium = False
            if user.subscription_type == 'premium' and user.subscription_expiry:
                if user.subscription_expiry > now_time:
                    is_premium = True
                elif (now_time - user.subscription_expiry) < timedelta(days=2):
                    is_premium = True
                    logger.info(f"⏳ User {user.id} is in GRACE PERIOD.")
                else:
                    user.subscription_type = 'free'
                    await db.commit()
                    logger.info(f"📉 User {user.id} AUTO-DOWNGRADED.")

            # 5. Format Grouped Message (Burst Protection + Conversion Engine)
            missed_context = await self._get_missed_slots_context(user.id, is_premium, db)
            message_body = self._format_alert(country, center, new_for_user, confidence, is_premium, missed_context)
            
            # 6. Tiered Delivery
            if is_premium:
                asyncio.create_task(self._safe_send(chat_id, message_body))
            else:
                asyncio.create_task(self._delayed_safe_send(chat_id, message_body, 180))
            
            # 7. Smart Conversion Trigger (Sprint G2)
            if not is_premium:
                await self._evaluate_conversion_triggers(user, center, db)
            
            # 8. Update Daily Stats (Sprint 4)
            await self._update_stats(user.id, len(slots), 1 if is_premium else 0, db)
            sent_count += 1

        logger.info(f"📤 ALERT SUMMARY: {center} | Sent: {sent_count} | Skipped: {skipped_duplicates}")

    async def _safe_send(self, chat_id: str, text: str):
        async with self.telegram_semaphore:
            await telegram_service.send_message(chat_id, text)
            await asyncio.sleep(0.05) 

    async def _delayed_safe_send(self, chat_id: str, text: str, delay: int):
        await asyncio.sleep(delay)
        await self._safe_send(chat_id, text)

    def _format_alert(self, country: str, center: str, slots: List[Dict], confidence: float, is_premium: bool, missed_context: str) -> str:
        conf_percent = int(confidence * 100)
        status_emoji = "🟢" if conf_percent > 80 else "🟡"
        
        sorted_slots = sorted(slots, key=lambda x: x['slot_date'])
        slot_list = "\n".join([f"• {s['slot_date'].strftime('%d %B')} – {s['slot_time']}" for s in sorted_slots[:8]])
        
        urgency = "\n🔥 <b>HIGH DEMAND: Slots filling fast!</b>" if len(slots) < 3 else ""
        premium_badge = "⚡ <b>Priority Alert</b> (Instant)" if is_premium else "⏳ <b>Delayed Alert</b> (3m delay)"
        
        social_proof = self._get_social_proof(center)
        scarcity = "\n⚠️ <b>Limited slots — high demand</b>"
        
        msg = (
            f"🇫🇷 <b>{country} - {center}</b>\n\n"
            f"{status_emoji} <b>CONFIDENCE ({conf_percent}%)</b>\n"
            f"⚡ {premium_badge}\n"
            f"🕒 Last seen: Just now\n\n"
            f"📅 <b>Available Slots:</b>\n"
            f"{slot_list}\n"
            f"{urgency}\n"
            f"{social_proof}"
            f"{scarcity}\n\n"
            f"{missed_context}"
            f"👉 <a href='https://visa.vfsglobal.com/'>Act fast — slots fill quickly</a>"
        )
        return msg

    def _get_social_proof(self, center: str) -> str:
        """Returns a simulated social proof message."""
        import random
        # Mocking logic: random number between 5 and 15
        count = random.randint(5, 15)
        return f"🔥 <b>{count} users booked {center} today</b>\n"

    async def _evaluate_conversion_triggers(self, user: User, center: str, db: AsyncSession):
        """Evaluates if an upgrade prompt should be shown (Sprint G2)."""
        today = datetime.now().date()
        
        # 1. Throttling: Max 2 prompts per day
        stats_stmt = select(UserDailyStats).where(and_(UserDailyStats.user_id == user.id, UserDailyStats.date == today))
        stats = (await db.execute(stats_stmt)).scalars().first()
        
        if stats and stats.prompts_shown >= 2:
            return

        # 2. Trigger Evaluation
        trigger = None
        missed = (stats.slots_found - stats.alerts_sent) if stats else 0
        
        # Trigger A: Missed Slots (Loss Aversion)
        if missed >= 2:
            trigger = "missed_slots"
        
        # Trigger B: Peak Hour (Anticipated Value)
        else:
            peak_h = await telegram_service._get_peak_hour(center)
            if peak_h is not None and datetime.now().hour == peak_h:
                trigger = "peak_hour"
        
        # Trigger C: Alert Threshold (Habit Formation)
        if not trigger and stats and stats.alerts_sent >= 3:
            trigger = "alert_threshold"

        # 3. Show Prompt
        if trigger:
            await self._send_upgrade_prompt(user, trigger, missed, db)

    async def _send_upgrade_prompt(self, user: User, trigger: str, missed: int, db: AsyncSession):
        """Sends the contextual upgrade prompt with inline button."""
        prompts = {
            "missed_slots": f"⚠️ <b>Loss Detected:</b> You've missed <b>{missed} slots</b> today due to 3-minute delay.\n\nDon't let the next one slip away. Upgrade now for <b>INSTANT</b> alerts.",
            "peak_hour": f"🔥 <b>Peak Window:</b> We are entering the highest activity hour for your center.\n\nPremium users are receiving alerts <b>180 seconds</b> before you. Join them now.",
            "alert_threshold": "📊 <b>High Activity:</b> You've received several alerts today. Slots are moving fast.\n\nUpgrade to Premium for the absolute advantage."
        }
        
        msg = prompts.get(trigger, "🚀 Upgrade to Premium for instant alerts and priority delivery.")
        
        # Inline Button for Stripe Checkout
        from .payment_service import payment_service
        try:
            checkout_url = await payment_service.create_checkout_session(str(user.id), user.email)
            keyboard = {
                "inline_keyboard": [[{"text": "⚡ Upgrade Now (£4.99)", "url": checkout_url}]]
            }
            
            await telegram_service.send_message(user.telegram_chat_id, msg, reply_markup=keyboard)
            
            # Log & Track
            await self._update_stats(user.id, 0, 0, db, prompt_increment=1)
            await self._log_conversion_event(user.id, trigger, "shown", db)
            logger.info(f"🎯 CONVERSION PROMPT: {user.id} | Trigger: {trigger}")
        except:
            pass

    async def _log_conversion_event(self, user_id: str, trigger: str, action: str, db: AsyncSession):
        log = ConversionLog(user_id=user_id, trigger_type=trigger, action=action)
        db.add(log)
        await db.commit()

    async def _update_stats(self, user_id: str, found_count: int, sent_count: int, db: AsyncSession, prompt_increment: int = 0):
        today = datetime.now().date()
        try:
            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(UserDailyStats).values(
                user_id=user_id, date=today, slots_found=found_count, alerts_sent=sent_count, prompts_shown=prompt_increment
            ).on_conflict_do_update(
                constraint='uq_user_date_stats',
                set_={
                    'slots_found': UserDailyStats.slots_found + found_count,
                    'alerts_sent': UserDailyStats.alerts_sent + sent_count,
                    'prompts_shown': UserDailyStats.prompts_shown + prompt_increment
                }
            )
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            logger.error(f"Error updating stats: {e}")

    async def _get_missed_slots_context(self, user_id: str, is_premium: bool, db: AsyncSession) -> str:
        if is_premium:
            return "💎 <i>As a Premium user, you received this instantly.</i>\n\n"
        try:
            today = datetime.now().date()
            stmt = select(UserDailyStats).where(and_(UserDailyStats.user_id == user_id, UserDailyStats.date == today))
            res = await db.execute(stmt)
            stats = res.scalars().first()
            if stats and stats.slots_found > stats.alerts_sent:
                missed = stats.slots_found - stats.alerts_sent
                return f"⚠️ <b>You missed {missed} slots today</b> due to delay.\n🚀 /upgrade to catch them instantly!\n\n"
        except: pass
        return "⏳ Upgrade to Premium for instant alerts!\n\n"

# Singleton
alert_dispatcher = AlertDispatcher()
