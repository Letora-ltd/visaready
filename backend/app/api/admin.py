from datetime import datetime, timezone, timedelta
from typing import Any

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..database.session import get_db
from ..models.entities import AppointmentStatus, PortalMapping, AppointmentStatusHistory, AdminStats, UpdateLog
from ..workers.ingest import run_ingestion
from ..core.logic import calculate_confidence
from ..core.security import RoleChecker

router = APIRouter(prefix='/api/admin', tags=['admin'])
admin_only = RoleChecker(['admin'])

def _norm_country(country: str) -> str:
    return (country or '').strip().upper()

def _norm_city(city: str) -> str:
    return '-'.join((city or '').strip().lower().split())

def _portal_payload(row: PortalMapping) -> dict[str, Any]:
    return {
        'id': row.id,
        'country': row.country,
        'city': row.city,
        'visa_type': row.visa_type,
        'country_code': row.country_code,
        'city_slug': row.city_slug,
        'provider': row.provider,
        'portal_url': row.portal_url,
        'instructions': row.instructions or [],
        'portal_status': row.portal_status,
        'last_health_checked': row.last_health_checked,
    }

class PortalIn(BaseModel):
    country: str
    city: str
    visa_type: str
    provider: str
    portal_url: str
    instructions: list[str] = Field(default_factory=list)
    updated_by: str | None = None

class StatusUpdateIn(BaseModel):
    country: str
    city: str
    visa_type: str
    status: str
    next_available_date: datetime | None = None
    verified_by: str
    notes: str | None = None
    expected_version: int

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str):
        if v.upper() not in ['AVAILABLE', 'LIMITED', 'NONE']:
            raise ValueError('Invalid status')
        return v.upper()

    @model_validator(mode='after')
    def validate_date(self):
        status = self.status
        date = self.next_available_date
        if status == 'NONE' and date is not None:
            raise ValueError('Next available date must be NULL if status is NONE')
        if status == 'AVAILABLE' and date is None:
            raise ValueError('Next available date must NOT be NULL if status is AVAILABLE')
        if status == 'LIMITED' and date is not None:
            if date.replace(tzinfo=None) < datetime.now():
                raise ValueError('Next available date must be in the future')
        return self

@router.post('/update')
async def admin_update(payload: dict, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    # Note: run_ingestion would also need to be async if it does DB work
    # For now, keeping it as is or marking for future async fix
    return run_ingestion(db, payload.get('provider', 'mock'))

@router.get('/tasks')
async def admin_tasks(limit: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    stmt = select(AppointmentStatus).order_by(
        AppointmentStatus.last_checked.asc().nullsfirst(), 
        AppointmentStatus.last_updated.asc()
    ).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    
    data = [
        {
            'id': r.id,
            'country': r.country,
            'city': r.city,
            'visa_type': r.visa_type,
            'availability_status': r.availability_status,
            'last_updated': r.last_updated,
            'last_checked': r.last_checked,
            'version': getattr(r, 'version', 1),
            'confidence_score': getattr(r, 'confidence_score', 0),
            'verified_by': getattr(r, 'verified_by', None)
        }
        for r in rows
    ]
    return {'success': True, 'data': data}

@router.post('/status/{status_id}/check')
async def mark_checked(
    status_id: int, 
    verified_by: str | None = Query(None), 
    notes: str | None = Query(None), 
    db: AsyncSession = Depends(get_db), 
    _ = Depends(admin_only)
):
    row = await db.get(AppointmentStatus, status_id)
    if not row:
        raise HTTPException(status_code=404, detail='status_not_found')
    
    now = datetime.now(timezone.utc)
    row.last_checked = now
    
    if verified_by:
        row.verified_by = verified_by
        # Update Stats
        stats_stmt = select(AdminStats).where(AdminStats.admin_id == verified_by)
        stats_res = await db.execute(stats_stmt)
        stats = stats_res.scalar_one_or_none()
        
        if not stats:
            stats = AdminStats(admin_id=verified_by, total_updates=1)
            db.add(stats)
        else:
            stats.total_updates += 1
            stats.last_active = now

    if notes:
        row.verification_notes = notes
    
    row.confidence_score = calculate_confidence(row.last_updated, 'admin')
    await db.commit()
    return {'success': True, 'data': {'id': row.id, 'confidence_score': row.confidence_score}}

@router.post('/status/manual-update')
async def manual_update(payload: StatusUpdateIn, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    c = _norm_country(payload.country)
    slug = _norm_city(payload.city)
    vt = payload.visa_type.strip().upper()
    
    stmt = select(AppointmentStatus).where(
        AppointmentStatus.country_code == c,
        AppointmentStatus.city_slug == slug,
        AppointmentStatus.visa_type == vt
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    if not row:
        row = AppointmentStatus(
            country=payload.country,
            city=payload.city,
            visa_type=vt,
            country_code=c,
            city_slug=slug,
            availability_status=payload.status,
            freshness_label='human_verified',
            last_updated=now,
            last_checked=now,
            next_available_date=payload.next_available_date,
            verified_by=payload.verified_by,
            verification_notes=payload.notes,
            version=1
        )
        db.add(row)
        await db.flush()
        # Initial history
        db.add(AppointmentStatusHistory(
            status_id=row.id,
            old_status=None,
            new_status=payload.status,
            old_next_date=None,
            new_next_date=payload.next_available_date,
            changed_by=payload.verified_by
        ))
    else:
        # Conflict control
        if getattr(row, 'version', 1) != payload.expected_version:
            raise HTTPException(status_code=409, detail={
                "error": "conflict",
                "message": "Data has been modified by another user",
                "latest_data": {
                    "version": getattr(row, 'version', 1),
                    "last_updated": row.last_updated,
                    "status": row.availability_status
                }
            })
            
        # Capture history
        history = AppointmentStatusHistory(
            status_id=row.id,
            old_status=row.availability_status,
            new_status=payload.status,
            old_next_date=row.next_available_date,
            new_next_date=payload.next_available_date,
            changed_by=payload.verified_by
        )
        db.add(history)
        
        # Update row
        if row.availability_status != payload.status or row.next_available_date != payload.next_available_date:
            row.last_updated = now
        
        row.availability_status = payload.status
        row.next_available_date = payload.next_available_date
        row.last_checked = now
        row.verified_by = payload.verified_by
        row.verification_notes = payload.notes
        row.freshness_label = 'human_verified'
        if hasattr(row, 'version'):
            row.version += 1
        else:
            row.version = 1

    # Update Admin Stats
    stats_stmt = select(AdminStats).where(AdminStats.admin_id == payload.verified_by)
    stats_res = await db.execute(stats_stmt)
    stats = stats_res.scalar_one_or_none()
    
    if not stats:
        stats = AdminStats(admin_id=payload.verified_by, total_updates=1)
        db.add(stats)
    else:
        stats.total_updates += 1
        stats.last_active = now

    # Log the update
    db.add(UpdateLog(
        provider='admin',
        status='success',
        records_upserted=1,
        route_id=row.id,
        source='admin'
    ))

    row.confidence_score = calculate_confidence(row.last_updated, 'admin')
    await db.commit()
    return {'success': True, 'data': {'id': row.id, 'confidence_score': row.confidence_score, 'version': getattr(row, 'version', 1)}}

@router.get('/portal-link')
async def portal_link(country: str, city: str, visa_type: str, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    c = _norm_country(country)
    slug = _norm_city(city)
    vt = visa_type.strip().upper()
    
    stmt = select(PortalMapping).where(
        or_(PortalMapping.country == c, PortalMapping.country_code == c),
        PortalMapping.city_slug == slug,
        PortalMapping.visa_type == vt,
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    
    if not row:
        return {
            'error': 'portal_mapping_not_found',
            'message': 'No portal mapping exists',
            'suggestion': 'Add mapping via admin panel',
        }
    return {'success': True, 'data': _portal_payload(row)}

@router.get('/portal')
async def list_portal(db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    stmt = select(PortalMapping).order_by(PortalMapping.country_code, PortalMapping.city_slug)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {'success': True, 'data': [_portal_payload(r) for r in rows]}

@router.post('/portal')
async def create_portal(payload: PortalIn, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    row = PortalMapping(
        country=payload.country,
        city=payload.city,
        visa_type=payload.visa_type.upper(),
        country_code=_norm_country(payload.country),
        city_slug=_norm_city(payload.city),
        provider=payload.provider,
        portal_url=payload.portal_url,
        instructions=payload.instructions,
        updated_by=payload.updated_by
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {'success': True, 'data': _portal_payload(row)}

@router.put('/portal/{portal_id}')
async def update_portal(portal_id: int, payload: PortalIn, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    row = await db.get(PortalMapping, portal_id)
    if not row:
        raise HTTPException(status_code=404, detail='portal_not_found')
    row.country = payload.country
    row.city = payload.city
    row.visa_type = payload.visa_type.upper()
    row.country_code = _norm_country(payload.country)
    row.city_slug = _norm_city(payload.city)
    row.provider = payload.provider
    row.portal_url = payload.portal_url
    row.instructions = payload.instructions
    row.updated_by = payload.updated_by
    await db.commit()
    await db.refresh(row)
    return {'success': True, 'data': _portal_payload(row)}

@router.post('/portal/{portal_id}/health')
async def portal_health(portal_id: int, timeout_seconds: float = 3.0, db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    row = await db.get(PortalMapping, portal_id)
    if not row:
        raise HTTPException(status_code=404, detail='portal_not_found')
    started = datetime.now(timezone.utc)
    status = 'down'
    try:
        # Note: requests is sync, but here we can afford it as it's a specific health check route
        # Ideally would use httpx.AsyncClient
        r = requests.head(row.portal_url, timeout=timeout_seconds, allow_redirects=True)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        status = 'reachable' if r.ok and elapsed < 1.2 else 'slow' if r.ok else 'down'
    except Exception:
        status = 'down'
    row.portal_status = status
    row.last_health_checked = datetime.now(timezone.utc)
    await db.commit()
    return {'success': True, 'data': {'portal_id': portal_id, 'portal_status': status, 'last_health_checked': row.last_health_checked}}

@router.get('/stats')
async def get_admin_stats(db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    stmt = select(AdminStats).order_by(AdminStats.total_updates.desc())
    result = await db.execute(stmt)
    stats = result.scalars().all()
    return {'success': True, 'data': stats}

@router.get('/system-health')
async def get_system_health(db: AsyncSession = Depends(get_db), _ = Depends(admin_only)):
    now = datetime.now(timezone.utc)
    stale_limit = now - timedelta(days=1)
    
    stale_stmt = select(AppointmentStatus).where(AppointmentStatus.last_updated < stale_limit)
    stale_res = await db.execute(stale_stmt)
    stale_routes = stale_res.scalars().all()
    
    logs_stmt = select(UpdateLog).where(UpdateLog.status == 'failed').order_by(UpdateLog.created_at.desc()).limit(50)
    logs_res = await db.execute(logs_stmt)
    failed_logs = logs_res.scalars().all()
    
    return {
        'success': True,
        'data': {
            'stale_routes_count': len(stale_routes),
            'stale_routes': [{'id': r.id, 'country': r.country, 'city': r.city, 'last_updated': r.last_updated} for r in stale_routes[:10]],
            'recent_failures': failed_logs,
            'system_status': 'optimal' if len(stale_routes) < 5 else 'degraded'
        }
    }
