from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from ..database.session import get_db
from ..models.entities import User, Slot, AlertPreference, SlotEvent, SlotHistory, SlotPattern
from ..schemas.vixaa import (
    UserCreate, UserRead, AlertPreferenceCreate, SlotRead, 
    SlotReportCreate, SlotEventRead, RecommendationRead, 
    HistoryRead, HistoryItem, DashboardRead
)
from ..services.reporting_service import process_slot_report
from ..services.pattern_service import get_recommendation

router = APIRouter(prefix="/api/vixaa", tags=["vixaa"])

@router.get("/recommendations", response_model=RecommendationRead)
async def get_rec(country: str, center: str, db: AsyncSession = Depends(get_db)):
    return await get_recommendation(db, country, center)

@router.get("/history", response_model=HistoryRead)
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
    
    return {
        "country": country,
        "center": center,
        "history": [HistoryItem(date=h.date, total_events=h.total_events, avg_confidence=h.avg_confidence) for h in history]
    }

@router.get("/dashboard", response_model=DashboardRead)
async def get_dashboard(user_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Preferences
    pref_stmt = select(AlertPreference).where(AlertPreference.user_id == user_id)
    pref_res = await db.execute(pref_stmt)
    prefs = pref_res.scalars().all()
    
    # 2. Recent Events
    event_stmt = select(SlotEvent).order_by(desc(SlotEvent.last_updated)).limit(5)
    event_res = await db.execute(event_stmt)
    recent_events = event_res.scalars().all()
    
    # 3. Recommendations (for first preference if exists)
    recs = []
    history_summary = None
    if prefs:
        p = prefs[0]
        rec = await get_recommendation(db, p.country, p.center)
        recs.append(rec)
        
        # History for first pref
        h_stmt = select(SlotHistory).where(
            and_(SlotHistory.country == p.country, SlotHistory.center == p.center)
        ).order_by(desc(SlotHistory.date)).limit(7)
        h_res = await db.execute(h_stmt)
        h_data = h_res.scalars().all()
        if h_data:
            history_summary = {
                "country": p.country,
                "center": p.center,
                "history": [HistoryItem(date=h.date, total_events=h.total_events, avg_confidence=h.avg_confidence) for h in reversed(h_data)]
            }

    return {
        "preferences": prefs,
        "recent_events": recent_events,
        "recommendations": recs,
        "history_summary": history_summary
    }

@router.post("/reports/submit")
async def submit_report(report_in: SlotReportCreate, user_id: str, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await process_slot_report(db, user, report_in.dict())
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result

@router.get("/events", response_model=List[SlotEventRead])
async def get_events(country: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(SlotEvent)
    if country:
        stmt = stmt.where(SlotEvent.country == country)
    
    result = await db.execute(stmt.order_by(SlotEvent.slot_date.asc()))
    events = result.scalars().all()
    return events

@router.post("/users", response_model=UserRead)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        return existing_user
    
    new_user = User(email=user_in.email, telegram_chat_id=user_in.telegram_chat_id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/alerts", status_code=status.HTTP_201_CREATED)
async def create_alert(alert_in: AlertPreferenceCreate, db: AsyncSession = Depends(get_db)):
    from ..services.subscription_service import is_premium
    user = await db.get(User, alert_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Feature Gating: Free users only get 1 alert preference
    if not is_premium(user):
        stmt = select(AlertPreference).where(AlertPreference.user_id == user.id)
        res = await db.execute(stmt)
        if len(res.scalars().all()) >= 1:
            raise HTTPException(
                status_code=403, 
                detail="Free tier is limited to 1 tracked corridor. Upgrade to Premium for unlimited tracking!"
            )
    
    new_alert = AlertPreference(user_id=alert_in.user_id, country=alert_in.country, center=alert_in.center)
    db.add(new_alert)
    await db.commit()
    return {"status": "success", "message": "Alert preference saved"}

@router.get("/slots", response_model=List[SlotRead])
async def get_slots(country: str = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Slot)
    if country:
        stmt = stmt.where(Slot.country == country)
    
    result = await db.execute(stmt.order_by(Slot.slot_date.asc()))
    slots = result.scalars().all()
    return slots
