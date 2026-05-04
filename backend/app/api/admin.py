from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from ..core.config import settings
from ..database.session import get_db
from ..models.entities import AppointmentStatus, PortalMapping
from ..workers.ingest import run_ingestion

router = APIRouter(prefix='/admin', tags=['admin'])


def _require_admin(x_admin_key: str | None):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail='unauthorized')


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


@router.post('/update')
def admin_update(payload: dict, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    return run_ingestion(db, payload.get('provider', 'mock'))


@router.get('/tasks')
def admin_tasks(limit: int = Query(default=20, ge=1, le=100), x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    rows = db.scalars(select(AppointmentStatus).order_by(AppointmentStatus.last_checked.asc().nullsfirst(), AppointmentStatus.last_updated.asc()).limit(limit)).all()
    data = [
        {
            'id': r.id,
            'country': r.country,
            'city': r.city,
            'visa_type': r.visa_type,
            'availability_status': r.availability_status,
            'last_updated': r.last_updated,
            'last_checked': r.last_checked,
        }
        for r in rows
    ]
    return {'success': True, 'data': data}


@router.post('/status/{status_id}/check')
def mark_checked(status_id: int, verified_by: str | None = None, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    row = db.get(AppointmentStatus, status_id)
    if not row:
        raise HTTPException(status_code=404, detail='status_not_found')
    row.last_checked = datetime.now(timezone.utc)
    if verified_by:
        row.verified_by = verified_by
    db.commit()
    return {'success': True, 'data': {'id': row.id, 'last_checked': row.last_checked}}


@router.get('/portal-link')
def portal_link(country: str, city: str, visa_type: str, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    c = _norm_country(country)
    slug = _norm_city(city)
    vt = visa_type.strip().upper()
    row = db.scalar(select(PortalMapping).where(
        or_(PortalMapping.country == c, PortalMapping.country_code == c),
        PortalMapping.city_slug == slug,
        PortalMapping.visa_type == vt,
    ))
    if not row:
        return {
            'error': 'portal_mapping_not_found',
            'message': 'No portal mapping exists',
            'suggestion': 'Add mapping via admin panel',
        }
    return {'success': True, 'data': _portal_payload(row)}


@router.get('/portal')
def list_portal(x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    rows = db.scalars(select(PortalMapping).order_by(PortalMapping.country_code, PortalMapping.city_slug)).all()
    return {'success': True, 'data': [_portal_payload(r) for r in rows]}


@router.post('/portal')
def create_portal(payload: PortalIn, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    row = PortalMapping(
        country=payload.country,
        city=payload.city,
        visa_type=payload.visa_type.upper(),
        country_code=_norm_country(payload.country),
        city_slug=_norm_city(payload.city),
        provider=payload.provider,
        portal_url=payload.portal_url,
        instructions=payload.instructions,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {'success': True, 'data': _portal_payload(row)}


@router.put('/portal/{portal_id}')
def update_portal(portal_id: int, payload: PortalIn, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    row = db.get(PortalMapping, portal_id)
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
    db.commit()
    db.refresh(row)
    return {'success': True, 'data': _portal_payload(row)}


@router.post('/portal/{portal_id}/health')
def portal_health(portal_id: int, timeout_seconds: float = 3.0, x_admin_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    _require_admin(x_admin_key)
    row = db.get(PortalMapping, portal_id)
    if not row:
        raise HTTPException(status_code=404, detail='portal_not_found')
    started = datetime.now(timezone.utc)
    status = 'down'
    try:
        r = requests.head(row.portal_url, timeout=timeout_seconds, allow_redirects=True)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        status = 'reachable' if r.ok and elapsed < 1.2 else 'slow' if r.ok else 'down'
    except Exception:
        status = 'down'
    row.portal_status = status
    row.last_health_checked = datetime.now(timezone.utc)
    db.commit()
    return {'success': True, 'data': {'portal_id': portal_id, 'portal_status': status, 'last_health_checked': row.last_health_checked}}
