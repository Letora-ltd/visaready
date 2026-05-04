from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..core.config import settings
from ..workers.ingest import run_ingestion

router = APIRouter(prefix='/admin', tags=['admin'])

@router.post('/update')
def admin_update(payload: dict, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail='unauthorized')
    return run_ingestion(db, payload.get('provider', 'mock'))
