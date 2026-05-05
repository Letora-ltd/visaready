import json
import logging
import asyncio
from datetime import datetime
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import SlotEvent, SlotSnapshot, User, AlertPreference
from ..services.telegram_service import telegram_service
from ..services.alert_dispatcher import alert_dispatcher

async def process_slots_lifecycle(db: AsyncSession, country: str, center: str, new_slots: list):
    """
    Main change detection and lifecycle engine.
    """
    logging.info(f"Processing lifecycle for {country} - {center}...")
    
    # 1. Save Snapshot
    snapshot = SlotSnapshot(
        center=center,
        raw_data={"slots": new_slots}
    )
    db.add(snapshot)
    await db.flush()

    # 2. Update Slot Events
    # This is a simplified version: deactivate old, add new
    await db.execute(
        update(SlotEvent)
        .where(and_(SlotEvent.country == country, SlotEvent.center == center))
        .values(is_active=False)
    )
    
    events_to_add = []
    for s in new_slots:
        event = SlotEvent(
            country=country,
            center=center,
            visa_type=s.get("visa_type", "TOURIST"),
            slot_date=s.get("slot_date"),
            time_window=s.get("time_window"),
            is_active=True
        )
        events_to_add.add(event)
    
    db.add_all(events_to_add)
    await db.commit()

    # 3. Trigger Alerts
    if new_slots:
        await alert_dispatcher.dispatch(db, country, center, new_slots)
