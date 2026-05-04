from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database.session import get_db
from ..models.entities import User
from ..services.telegram_service import send_telegram_message

router = APIRouter(prefix="/api/bot", tags=["telegram-bot"])

@router.post("/webhook")
async def bot_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handles incoming messages from Telegram.
    """
    data = await request.json()
    message = data.get("message", {})
    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "")

    if not text or not chat_id:
        return {"status": "ok"}

    if text.startswith("/start"):
        await handle_start(chat_id, db)
    elif text.startswith("/status"):
        await handle_status(chat_id, db)
    elif text.startswith("/upgrade"):
        await handle_upgrade(chat_id)
    
    return {"status": "ok"}

async def handle_start(chat_id: str, db: AsyncSession):
    msg = (
        "🚀 <b>Welcome to Vixa Intelligence!</b>\n\n"
        "I am your visa slot assistant. Your Telegram ID is:\n"
        f"<code>{chat_id}</code>\n\n"
        "Copy this ID and paste it in the Vixa Dashboard to start receiving alerts.\n\n"
        "<b>Available Commands:</b>\n"
        "/status - Check your subscription\n"
        "/upgrade - Get Premium access"
    )
    send_telegram_message(chat_id, msg)

async def handle_status(chat_id: str, db: AsyncSession):
    stmt = select(User).where(User.telegram_chat_id == chat_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    
    if not user:
        msg = "❌ User not linked. Please add your Telegram ID to the Vixa Dashboard first."
    else:
        status = user.subscription_type.upper()
        expiry = user.subscription_expiry.strftime('%Y-%m-%d') if user.subscription_expiry else "N/A"
        msg = (
            f"👤 <b>Subscription Status</b>\n\n"
            f"Plan: <b>{status}</b>\n"
            f"Expiry: {expiry}\n\n"
            "Need more speed? Use /upgrade"
        )
    send_telegram_message(chat_id, msg)

async def handle_upgrade(chat_id: str):
    msg = (
        "💎 <b>Upgrade to Vixa Premium</b>\n\n"
        "Get the advantage you need to secure your appointment:\n\n"
        "✅ <b>Instant Alerts</b> (3 min faster than Free)\n"
        "✅ <b>Multiple Centers</b> tracking\n"
        "✅ <b>Priority Support</b>\n\n"
        "💳 <b>Price:</b> ₹999 / month\n\n"
        "👉 <a href='https://vixaa.online/premium'>Click here to Upgrade Now</a>"
    )
    send_telegram_message(chat_id, msg)
