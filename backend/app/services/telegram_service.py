import logging
import os
import httpx
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from ..models.entities import User, AlertPreference, UserDailyStats, Referral
import secrets
import string

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict] = None):
        """Sends a message to a Telegram chat."""
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    async def handle_webhook(self, update: Dict, db: AsyncSession):
        """Handles incoming updates from Telegram (Sprint G1 Enhanced)."""
        # 1. Handle Callback Queries (Buttons)
        if "callback_query" in update:
            await self.handle_callback_query(update["callback_query"], db)
            return

        if "message" not in update:
            return
            
        message = update["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        
        if text.startswith("/start"):
            # Check for referral parameter: /start ref_ABC123
            ref_code = None
            if len(text.split()) > 1:
                param = text.split()[1]
                if param.startswith("ref_"):
                    ref_code = param.replace("ref_", "")
            await self._handle_start(chat_id, db, ref_code)
        elif text.startswith("/status"):
            await self._handle_status(chat_id, db)
        elif text.startswith("/referral"):
            await self._handle_referral(chat_id, db)
        elif text.startswith("/centers"):
            await self._handle_centers(chat_id, db)
        elif text.startswith("/stop"):
            await self._handle_stop(chat_id, db)
        elif text.startswith("/upgrade"):
            await self._handle_upgrade(chat_id, db)
        elif text.startswith("/track") or text.startswith("/untrack"):
            await self.process_text_selection(chat_id, text, db)

    async def _handle_start(self, chat_id: str, db: AsyncSession, ref_code: str = None):
        """High-Conversion Onboarding (Sprint G1) + Referral Tracking (Sprint G3)."""
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        
        is_new = False
        if not user:
            is_new = True
            user = User(
                email=f"tg_{chat_id}@vixaa.internal",
                telegram_chat_id=chat_id,
                name=f"Telegram User {chat_id}",
                subscription_type="free",
                alerts_enabled=True,
                onboarding_completed=False,
                referral_code=self._generate_referral_code()
            )
            db.add(user)
            await db.commit()
            
            # Handle Referral (Sprint G3)
            if ref_code:
                await self._track_referral(user, ref_code, db)
            
        welcome_text = (
            "🚀 <b>Welcome to Vixaa!</b>\n\n"
            "Get visa slots before others with real-time tracking.\n\n"
            "⚡ <b>What you get:</b>\n"
            "• <b>Instant Slot Alerts</b> (Premium)\n"
            "• <b>Verified Availability</b> (No fake signals)\n"
            "• <b>Best Time Predictions</b> (Data-driven insights)\n\n"
            "👇 <b>Step 1: Select your center to start tracking</b>"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "📍 London", "callback_data": "track_London"}],
                [{"text": "📍 Manchester", "callback_data": "track_Manchester"}],
                [{"text": "📍 Edinburgh", "callback_data": "track_Edinburgh"}]
            ]
        }
        await self.send_message(chat_id, welcome_text, reply_markup=keyboard)

    async def handle_callback_query(self, query: Dict, db: AsyncSession):
        """Processes button clicks (Sprint G1)."""
        chat_id = str(query["message"]["chat"]["id"])
        data = query["data"]
        
        if data.startswith("track_"):
            center_name = data.replace("track_", "")
            result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
            user = result.scalars().first()
            if not user: return
            
            check = await db.execute(select(AlertPreference).where(
                and_(AlertPreference.user_id == user.id, AlertPreference.center == center_name)
            ))
            if not check.scalars().first():
                new_pref = AlertPreference(user_id=user.id, country="Belgium", center=center_name)
                db.add(new_pref)
            
            user.onboarding_completed = True
            await db.commit()
            await self._send_onboarding_demo(chat_id, center_name, db)

    async def _send_onboarding_demo(self, chat_id: str, center: str, db: AsyncSession):
        """Sends immediate value hook after center selection."""
        from ..core.intelligence import intelligence_engine
        peak_h = await self._get_peak_hour(center)
        
        peak_text = ""
        if peak_h is not None:
            peak_text = f"🔥 <b>Best time for {center}:</b> {peak_h:02}:00 – {peak_h+1:02}:00\n"
        
        demo_text = (
            f"✅ <b>Setup Complete!</b>\n\n"
            f"I am now tracking <b>{center}</b> for you.\n\n"
            f"📊 <b>Market Insight:</b>\n"
            f"{peak_text}"
            f"⚡ <b>Important:</b> You are currently on the <b>FREE</b> plan (3-minute alert delay).\n\n"
            f"💎 <b>Premium users</b> get alerts the exact second they appear.\n"
            f"Use /upgrade to remove the delay."
        )
        await self.send_message(chat_id, demo_text)

    async def _get_peak_hour(self, center: str) -> Optional[int]:
        """Finds the hour with the highest heat score for a center."""
        try:
            from ..core.intelligence import intelligence_engine
            max_score = 0
            best_h = None
            for h in range(24):
                score = await intelligence_engine.get_center_score(center, h)
                if score > max_score:
                    max_score = score
                    best_h = h
            return best_h
        except:
            return None

    async def _handle_referral(self, chat_id: str, db: AsyncSession):
        """Shows referral link and progress (Sprint G3)."""
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user: return

        # 1. Get referral count
        ref_count_stmt = select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
        count = (await db.execute(ref_count_stmt)).scalar() or 0
        
        needed = 2
        remaining = max(0, needed - count)
        
        link = f"https://t.me/vixaa_bot?start=ref_{user.referral_code}"
        
        msg = (
            "🎁 <b>Vixaa Referral Program</b>\n\n"
            "Invite friends and get <b>Premium</b> for free!\n\n"
            f"🔗 <b>Your Link:</b>\n<code>{link}</code>\n\n"
            f"👥 <b>Invited:</b> {count} users\n"
            f"🎯 <b>Goal:</b> {needed} friends\n\n"
            "🎁 <b>Reward:</b> 3 days of Premium for every 2 friends who join.\n\n"
            "🚀 <i>Tap the link above to copy and share!</i>"
        )
        await self.send_message(chat_id, msg)

    async def _track_referral(self, new_user: User, ref_code: str, db: AsyncSession):
        """Links new user to referrer."""
        stmt = select(User).where(User.referral_code == ref_code)
        referrer = (await db.execute(stmt)).scalars().first()
        
        if referrer and referrer.id != new_user.id:
            # Check if this user was already referred (prevent double tracking)
            new_ref = Referral(referrer_id=referrer.id, referred_id=new_user.id)
            db.add(new_ref)
            await db.commit()
            
            # 2. Check for reward
            await self._check_and_reward_referrals(referrer, db)
            logger.info(f"🤝 REFERRAL: {new_user.id} joined via {referrer.id}")

    async def _check_and_reward_referrals(self, referrer: User, db: AsyncSession):
        """Grants 3 days premium if 2 new referrals reached."""
        stmt = select(func.count(Referral.id)).where(
            and_(Referral.referrer_id == referrer.id, Referral.status == 'joined')
        )
        count = (await db.execute(stmt)).scalar() or 0
        
        if count >= 2:
            # Grant Reward
            from datetime import timedelta
            now = datetime.now()
            current_expiry = referrer.subscription_expiry if referrer.subscription_expiry and referrer.subscription_expiry > now else now
            
            referrer.subscription_type = 'premium'
            referrer.subscription_expiry = current_expiry + timedelta(days=3)
            
            # Update status to 'rewarded' for these referrals
            update_stmt = (
                update(Referral)
                .where(and_(Referral.referrer_id == referrer.id, Referral.status == 'joined'))
                .limit(2)
                .values(status='rewarded')
            )
            # SQLAlchemy limit in update is tricky, better fetch and update
            ref_stmt = select(Referral).where(and_(Referral.referrer_id == referrer.id, Referral.status == 'joined')).limit(2)
            to_update = (await db.execute(ref_stmt)).scalars().all()
            for r in to_update:
                r.status = 'rewarded'
            
            await db.commit()
            
            await self.send_message(
                referrer.telegram_chat_id,
                "🎁 <b>REWARD UNLOCKED!</b>\n\n"
                "You successfully invited 2 friends. We've added <b>3 days of Premium</b> to your account. 🚀"
            )

    def _generate_referral_code(self, length=8):
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    async def _handle_status(self, chat_id: str, db: AsyncSession):
        """Enhanced /status with stats and peak window (Sprint 4)."""
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        
        if not user:
            await self.send_message(chat_id, "Please use /start to register first.")
            return
            
        pref_result = await db.execute(select(AlertPreference).where(AlertPreference.user_id == user.id))
        prefs = pref_result.scalars().all()
        centers = [p.center for p in prefs] or ["None"]
        
        today = datetime.now().date()
        stats_result = await db.execute(select(UserDailyStats).where(
            and_(UserDailyStats.user_id == user.id, UserDailyStats.date == today)
        ))
        stats = stats_result.scalars().first()
        
        peak_info = ""
        if centers[0] != "None":
            peak_h = await self._get_peak_hour(centers[0])
            if peak_h is not None:
                peak_info = f"\n🔥 <b>Peak window ({centers[0]}):</b> {peak_h:02}:00 - {peak_h+1:02}:00"

        stats_text = ""
        if stats:
            missed = stats.slots_found - stats.alerts_sent
            stats_text = (
                f"\n📊 <b>Today's Activity:</b>\n"
                f"• Slots found: {stats.slots_found}\n"
                f"• Alerts received: {stats.alerts_sent}\n"
                f"• Missed: {missed} {'⚠️' if missed > 0 else '✅'}\n"
            )
        else:
            stats_text = "\n📊 <i>No activity recorded today yet.</i>\n"

        status_text = (
            f"👤 <b>User Status</b>\n\n"
            f"💳 Plan: <b>{user.subscription_type.upper()}</b>\n"
            f"📍 Tracking: {', '.join(centers)}\n"
            f"{stats_text}{peak_info}"
        )
        if user.subscription_type == 'free':
            status_text += "\n\n🚀 Upgrade to /upgrade for instant alerts!"
        await self.send_message(chat_id, status_text)

    async def _handle_centers(self, chat_id: str, db: AsyncSession):
        centers_text = (
            "<b>Available Centers</b>\n\n"
            "• London\n"
            "• Manchester\n"
            "• Edinburgh\n\n"
            "<b>Commands:</b>\n"
            "<code>/track london</code> - Start tracking\n"
            "<code>/untrack london</code> - Stop tracking"
        )
        await self.send_message(chat_id, centers_text)

    async def _handle_upgrade(self, chat_id: str, db: AsyncSession):
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user: return
        from .payment_service import payment_service
        try:
            checkout_url = await payment_service.create_checkout_session(str(user.id), user.email)
            msg = (
                "💎 <b>Upgrade to Vixaa Premium</b>\n\n"
                "✅ <b>Instant Alerts</b> (Priority)\n"
                "✅ <b>Multi-Center</b> tracking\n"
                "✅ <b>Verified Patterns</b>\n\n"
                f'👉 <a href="{checkout_url}">CLICK HERE TO UPGRADE NOW</a>'
            )
            await self.send_message(chat_id, msg)
        except Exception as e:
            await self.send_message(chat_id, "Sorry, I couldn't generate a checkout link right now.")

    async def _handle_stop(self, chat_id: str, db: AsyncSession):
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if user:
            from sqlalchemy import delete
            await db.execute(delete(AlertPreference).where(AlertPreference.user_id == user.id))
            await db.commit()
            await self.send_message(chat_id, "All alerts have been disabled. 🛑")

    async def process_text_selection(self, chat_id: str, text: str, db: AsyncSession):
        is_untrack = text.startswith("/untrack")
        cmd = "/untrack" if is_untrack else "/track"
        input_center = text.replace(cmd, "").strip().lower()
        valid_centers = ["london", "manchester", "edinburgh"]
        if not input_center:
            await self.send_message(chat_id, f"Please specify a center. Example: {cmd} london")
            return
        if input_center not in valid_centers:
            await self.send_message(chat_id, f"Center '{input_center}' not recognized.")
            return
        center_name = input_center.title()
        result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
        user = result.scalars().first()
        if not user: return
        if is_untrack:
            from sqlalchemy import delete
            await db.execute(delete(AlertPreference).where(and_(AlertPreference.user_id == user.id, AlertPreference.center == center_name)))
            await db.commit()
            await self.send_message(chat_id, f"🛑 Stopped tracking <b>{center_name}</b>.")
        else:
            check_result = await db.execute(select(AlertPreference).where(and_(AlertPreference.user_id == user.id, AlertPreference.center == center_name)))
            if check_result.scalars().first():
                await self.send_message(chat_id, f"You are already tracking <b>{center_name}</b>.")
                return
            new_pref = AlertPreference(user_id=user.id, country="Belgium", center=center_name)
            db.add(new_pref)
            await db.commit()
            await self.send_message(chat_id, f"✅ Now tracking <b>{center_name} (Belgium)</b>.")

# Compatibility Wrapper
def send_telegram_message(chat_id: str, text: str):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running(): loop.create_task(telegram_service.send_message(chat_id, text))
        else: loop.run_until_complete(telegram_service.send_message(chat_id, text))
    except: pass

telegram_service = TelegramService()
