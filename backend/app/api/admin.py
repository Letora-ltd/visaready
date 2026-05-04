from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..core.config import settings
from ..workers.ingest import run_ingestion
from ..services import visa_service

router = APIRouter(prefix='/admin', tags=['admin'])

class UpdateStatusIn(BaseModel):
    country: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=1, max_length=120)
    visa_type: str = Field(min_length=2, max_length=40)
    availability_status: str = Field(min_length=2, max_length=40)
    next_available_date: str | None = None
    notes: str | None = None


def _check_admin(x_admin_key: str | None):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail='unauthorized')

@router.get('/routes')
def admin_routes(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    return {"success": True, "data": visa_service.list_routes(db)}

@router.get('/status')
def admin_status(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    return {"success": True, "data": visa_service.get_all_status(db)}

@router.post('/update-status')
def admin_update_status(payload: UpdateStatusIn, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    row, changed = visa_service.upsert_status(db, payload.model_dump(), actor='admin', source_type='admin')
    return {"success": True, "data": row, "meta": {"changed": changed}}

@router.get('/tasks')
def admin_tasks(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    return {"success": True, "data": visa_service.get_tasks(db)}

@router.post('/tasks/{task_id}/complete')
def admin_task_complete(task_id: int, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    result = visa_service.complete_task(db, task_id, actor='admin')
    if not result:
        raise HTTPException(status_code=404, detail='task_not_found')
    return {"success": True, "data": result}

@router.post('/update')
def admin_update(payload: dict, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _check_admin(x_admin_key)
    return run_ingestion(db, payload.get('provider', 'safe_public'))
