from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from ..database.session import get_db
from ..models.entities import User, AlertPreference, SlotEvent, SlotHistory, SlotPattern
# Note: legacy schemas might be missing, so we'll return dicts if needed
# but let's assume they might be fixed or unused for this run
from ..core.logging import logger
import logging
import uuid

router = APIRouter(prefix="/api/vixaa", tags=["vixaa"])

@router.get("/recommendations")
async def get_rec(country: str, center: str, db: AsyncSession = Depends(get_db)):
    # Legacy service call
    from ..services.pattern_service import get_recommendation
    return await get_recommendation(db, country, center)

@router.get("/history")
async def get_history(country: str, center: str, db: AsyncSession = Depends(get_db)):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    stmt = select(SlotHistory).where(
        and_(
            SlotHistory.country == country,
            SlotHistory.center == center,
            SlotHistory.date >= seven_days_ago
        )
    ).order_by(SlotHistory.date.asc())
    
    res = await db.execute(stmt)
    history = res.scalars().all()
    return history

@router.get("/dashboard")
async def get_dashboard(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        # ... logic using SlotEvent
        event_stmt = select(SlotEvent).order_by(desc(SlotEvent.last_updated)).limit(5)
        event_res = await db.execute(event_stmt)
        recent_events = event_res.scalars().all()
        return {"recent_events": recent_events}
    except Exception as e:
        logger.error(f"Dashboard Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/slots")
async def get_slots(country: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SlotEvent)
    if country:
        stmt = stmt.where(SlotEvent.country == country)
    result = await db.execute(stmt.order_by(SlotEvent.slot_date.asc()))
    slots = result.scalars().all()
    return slots
