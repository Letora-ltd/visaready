from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..database.session import AsyncSessionLocal
from ..models.entities import User, UserDailyStats, ActivityLog, SlotEvent, AlertPreference, Referral
from ..core.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/user")
async def get_user_dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns data for the user dashboard (UI-1)."""
    today = datetime.now().date()
    
    # 1. Get Today's Stats
    stats_stmt = select(UserDailyStats).where(
        and_(UserDailyStats.user_id == user.id, UserDailyStats.date == today)
    )
    stats = (await db.execute(stats_stmt)).scalars().first()
    
    # 2. Get Tracking Info
    pref_stmt = select(AlertPreference).where(AlertPreference.user_id == user.id).limit(1)
    pref = (await db.execute(pref_stmt)).scalars().first()
    center = pref.center if pref else "None"
    
    # 3. Get Peak Window Insight
    peak_window = "14:00-15:00" # Default
    if pref:
        # Simplified: find hour with most logs
        peak_stmt = select(ActivityLog.hour, func.count(ActivityLog.id)).where(
            ActivityLog.center == pref.center
        ).group_by(ActivityLog.hour).order_by(func.count(ActivityLog.id).desc()).limit(1)
        peak_res = await db.execute(peak_stmt)
        peak_row = peak_res.first()
        if peak_row:
            h = peak_row[0]
            peak_window = f"{h:02}:00 - {h+1:02}:00"

    # 4. Recent Activity (Live Feed)
    recent_slots_stmt = select(SlotEvent).where(
        SlotEvent.center == center if pref else True
    ).order_by(SlotEvent.last_updated.desc()).limit(5)
    recent_slots = (await db.execute(recent_slots_stmt)).scalars().all()
    
    return {
        "user_name": user.name or user.email.split("@")[0],
        "plan": user.subscription_type,
        "center": center,
        "slots_found": stats.slots_found if stats else 0,
        "alerts_sent": stats.alerts_sent if stats else 0,
        "missed": (stats.slots_found - stats.alerts_sent) if stats else 0,
        "peak_window": peak_window,
        "first_session": not user.onboarding_completed,
        "recent_activity": [
            {
                "date": s.slot_date.strftime("%d %B"),
                "time": s.time_window,
                "confidence": s.confidence_score,
                "timestamp": s.last_updated.isoformat()
            } for s in recent_slots
        ]
    }

@router.get("/intelligence")
async def get_intelligence(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns data for intelligence visualization (UI-2)."""
    # 1. Get Tracking Preference
    pref_stmt = select(AlertPreference).where(AlertPreference.user_id == user.id).limit(1)
    pref = (await db.execute(pref_stmt)).scalars().first()
    center = pref.center if pref else "London" # Fallback to London for demo
    
    # 2. Get Heatmap Data (Hourly)
    heatmap = [0.0] * 24
    peak_stmt = select(ActivityLog.hour, func.count(ActivityLog.id)).where(
        ActivityLog.center == center
    ).group_by(ActivityLog.hour)
    peak_res = await db.execute(peak_stmt)
    for row in peak_res.all():
        heatmap[row[0]] = float(row[1])
        
    # Normalize Heatmap (0-1)
    max_h = max(heatmap) if any(heatmap) else 1.0
    heatmap = [round(h / max_h, 2) for h in heatmap]

    # 3. Slot Timeline (Chronological flow)
    timeline_stmt = select(SlotEvent).where(SlotEvent.center == center).order_by(SlotEvent.last_updated.desc()).limit(10)
    timeline_res = await db.execute(timeline_stmt)
    timeline_slots = timeline_res.scalars().all()
    
    # 4. Activity Trend (Morning/Afternoon/Evening)
    morning = sum(heatmap[6:12])
    afternoon = sum(heatmap[12:18])
    evening = sum(heatmap[18:24])
    night = sum(heatmap[0:6])

    return {
        "center": center,
        "heatmap": heatmap,
        "timeline": [
            {
                "event": "Drop Detected",
                "time": s.last_updated.isoformat(),
                "slots": 1, # Placeholder
                "confidence": s.confidence_score
            } for s in timeline_slots
        ],
        "avg_slot_lifetime": 145, # Simulated seconds (derived from scraper logic)
        "trends": {
            "morning": round(morning, 2),
            "afternoon": round(afternoon, 2),
            "evening": round(evening, 2),
            "night": round(night, 2)
        }
    }

@router.get("/conversion")
async def get_conversion_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns data for conversion triggers (UI-3)."""
    today = datetime.now().date()
    stats_stmt = select(UserDailyStats).where(
        and_(UserDailyStats.user_id == user.id, UserDailyStats.date == today)
    )
    stats = (await db.execute(stats_stmt)).scalars().first()
    
    missed = (stats.slots_found - stats.alerts_sent) if stats else 0
    
    return {
        "missed_today": missed,
        "avg_lifetime": 145, # seconds
        "user_delay": 180 if user.subscription_type == "free" else 0,
        "comparison": [
            {"feature": "Alert Speed", "free": "3 min delay", "premium": "Instant ⚡"},
            {"feature": "Missed Slots", "free": "High probability", "premium": "None ✅"},
            {"feature": "Tracking", "free": "1 Center", "premium": "Unlimited"},
            {"feature": "Intelligence", "free": "Basic", "premium": "Full Access"}
        ],
        "success_story": "🔥 High booking activity detected today"
    }

@router.get("/referral")
async def get_referral_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns data for referral dashboard (UI-3)."""
    ref_count_stmt = select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
    count = (await db.execute(ref_count_stmt)).scalar() or 0
    
    return {
        "invite_link": f"https://t.me/vixaa_bot?start=ref_{user.referral_code}",
        "invited_count": count,
        "target_count": 2,
        "reward": "3 Days Premium"
    }

@router.get("/admin/health")
async def get_admin_health(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Mocked/derived system health
    return {
        "status": "HEALTHY",
        "success_rate": 98.4,
        "queue_size": 0,
        "failure_rate": 1.6,
        "active_sessions": 2
    }

@router.get("/admin/metrics")
async def get_admin_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    premium_users = (await db.execute(select(func.count(User.id)).where(User.subscription_type == "premium"))).scalar()
    
    # Revenue estimate (mock)
    revenue = premium_users * 4.99
    
    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "active_today": int(total_users * 0.4), # Simulated activity
        "revenue_today": round(revenue / 30, 2),
        "mrr": round(revenue, 2)
    }

@router.get("/admin/slots")
async def get_admin_slots(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    stmt = select(SlotEvent).order_by(SlotEvent.last_updated.desc()).limit(20)
    slots = (await db.execute(stmt)).scalars().all()
    
    return [
        {
            "center": s.center,
            "date": s.slot_date.strftime("%d %B"),
            "time": s.time_window,
            "confidence": s.confidence_score,
            "updated": s.last_updated.isoformat()
        } for s in slots
    ]
