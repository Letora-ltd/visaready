from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.session import get_db
from ..services import visa_service

router = APIRouter(prefix='/api/visa', tags=['visa'])

@router.get('/routes')
async def routes(db: AsyncSession = Depends(get_db)):
    data = await visa_service.list_routes(db)
    return {"success": True, "data": data}

@router.get('/status')
async def status(country: str = Query(..., min_length=2, max_length=2), visa_type: str | None = None, db: AsyncSession = Depends(get_db)):
    rows = await visa_service.get_status(db, origin=country, destination=visa_type)
    data = [{
        "country": r.country, 
        "center": r.center, 
        "visa_type": r.visa_type, 
        "last_updated": r.last_updated,
        "is_active": r.is_active
    } for r in rows]
    return {"success": True, "data": data, "meta": {"count": len(data)}}

@router.get('/last-updated')
async def get_last_updated(db: AsyncSession = Depends(get_db)):
    lu = await visa_service.last_updated(db)
    return {"success": True, "data": {"last_updated": lu}}
