from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..services import visa_service

router = APIRouter(prefix='/visa', tags=['visa'])

@router.get('/routes')
def routes(db: Session = Depends(get_db)):
    return {"success": True, "data": visa_service.list_routes(db)}

@router.get('/status')
def status(country: str = Query(..., min_length=2, max_length=2), visa_type: str | None = None, db: Session = Depends(get_db)):
    data = visa_service.get_status(db, country, visa_type)
    return {"success": True, "data": data, "meta": {"count": len(data)}}

@router.get('/last-updated')
def get_last_updated(db: Session = Depends(get_db)):
    return {"success": True, "data": {"last_updated": visa_service.last_updated(db)}}
