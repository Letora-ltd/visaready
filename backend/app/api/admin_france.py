from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from ..database.session import get_db
from ..models.entities import Session, Slot
from ..workers.jobs import check_and_alert_job

router = APIRouter(prefix="/api/admin/france", tags=["admin-france"])

@router.get("/sessions", response_model=List[dict])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    stmt = select(SessionRecord).order_by(desc(SessionRecord.last_used))
    res = await db.execute(stmt)
    return [{"id": s.id, "session_id": s.session_id, "is_active": s.is_active, "reuse_count": s.reuse_count, "last_used": s.last_used} for s in res.scalars().all()]

@router.post("/trigger-check")
async def trigger_check(db: AsyncSession = Depends(get_db)):
    """
    Manually triggers the slot check job.
    """
    try:
        await check_and_alert_job(db)
        return {"status": "success", "message": "Manual check triggered and completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/reuse")
async def mark_session_reuse(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(SessionRecord, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.reuse_count += 1
    await db.commit()
    return {"status": "success", "reuse_count": session.reuse_count}
