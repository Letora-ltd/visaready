import json
import logging
import asyncio
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import Slot, SlotSnapshot, User, AlertPreference
from ..services.telegram_service import send_telegram_message

async def process_slots_lifecycle(db: AsyncSession, country: str, center: str, new_slots: list):
    """
    Main change detection and lifecycle engine.
    """
    logging.info(f"Processing lifecycle for {country} - {center}...")
    
    # 1. Save Snapshot
    snapshot = SlotSnapshot(
        country=country,
        center=center,
        raw_data=json.dumps([{**s, "slot_date": s["slot_date"].isoformat()} for s in new_slots])
    )
    db.add(snapshot)
    
    # 2. Get existing active slots for this corridor
    stmt = select(Slot).where(
        and_(
            Slot.country == country,
            Slot.center == center,
            Slot.is_active == True
        )
    )
    res = await db.execute(stmt)
    existing_slots = { (s.slot_date.date(), s.slot_time): s for s in res.scalars().all() }
    
    current_slots_keys = set()
    newly_found = []
    
    for slot_data in new_slots:
        key = (slot_data["slot_date"].date(), slot_data["slot_time"])
        current_slots_keys.add(key)
        
        if key in existing_slots:
            slot = existing_slots[key]
            slot.last_seen_at = datetime.utcnow()
            slot.seen_count += 1
            slot.last_checked = datetime.utcnow()
        else:
            new_slot = Slot(
                **slot_data,
                first_seen_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow(),
                seen_count=1,
                is_active=True,
                last_checked=datetime.utcnow()
            )
            db.add(new_slot)
            newly_found.append(slot_data)
            logging.info(f"✨ NEW SLOT DETECTED: {country} {center} on {slot_data['slot_date']}")

    removed_keys = set(existing_slots.keys()) - current_slots_keys
    for key in removed_keys:
        slot = existing_slots[key]
        slot.is_active = False

    if newly_found:
        await trigger_lifecycle_alerts(db, country, center, newly_found)

    await db.commit()
    return len(newly_found)

async def trigger_lifecycle_alerts(db: AsyncSession, country: str, center: str, new_slots: list):
    """
    Sends priority-based alerts.
    """
    alert_stmt = select(User).join(AlertPreference).where(
        and_(
            AlertPreference.country == country,
            AlertPreference.center == center,
            User.telegram_chat_id != None
        )
    )
    res = await db.execute(alert_stmt)
    users = res.scalars().all()
    
    for user in users:
        is_premium = user.subscription_type == 'premium' and (user.subscription_expiry and user.subscription_expiry > datetime.utcnow())
        
        if len(new_slots) > 3:
            message = (
                f"🚨 <b>MULTIPLE NEW SLOTS FOUND!</b>\n\n"
                f"📍 <b>Country:</b> {country}\n"
                f"🏢 <b>Center:</b> {center}\n"
                f"📅 <b>Count:</b> {len(new_slots)} new slots detected.\n\n"
            )
        else:
            message = "🚨 <b>NEW SLOTS DETECTED!</b>\n\n"
            for s in new_slots:
                message += f"📅 {s['slot_date'].strftime('%Y-%m-%d')} at {s['slot_time']}\n"
            message += f"\n📍 {country} ({center})\n"

        if is_premium:
            message += "⚡ <b>Priority Alert</b> (Instant)"
            send_telegram_message(user.telegram_chat_id, message)
        else:
            # Delayed alert for free users (FOMO)
            delay_msg = message + "\n\n⏳ <i>This alert was delayed by 3 minutes. Upgrade to Premium for instant alerts!</i>"
            # Schedule delayed task
            asyncio.create_task(delayed_alert(user.telegram_chat_id, delay_msg, delay_seconds=180))

async def delayed_alert(chat_id: str, message: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    send_telegram_message(chat_id, message)
