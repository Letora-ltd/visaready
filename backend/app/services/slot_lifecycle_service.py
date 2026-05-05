import json
import logging
import asyncio
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import Slot, SlotSnapshot, User, AlertPreference
from ..services.telegram_service import send_telegram_message
from ..services.alert_dispatcher import alert_dispatcher

async def process_slots_lifecycle(db: AsyncSession, country: str, center: str, new_slots: list):
    """
    Main change detection and lifecycle engine.
    """
    logging.info(f"Processing lifecycle for {country} - {center}...")
    
    # 1. Save Snapshot
    snapshot = SlotSnapshot(
        country=country,
        center=center,
        raw_response=json.dumps([{**s, "slot_date": s["slot_date"].isoformat() if hasattr(s["slot_date"], "isoformat") else s["slot_date"]} for s in new_slots])
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
        await alert_dispatcher.dispatch(db, country, center, newly_found)

    await db.commit()
    return len(newly_found)
