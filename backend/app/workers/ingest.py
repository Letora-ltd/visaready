from sqlalchemy import select
from sqlalchemy.orm import Session
from ..integrations.providers import MockProvider
from ..models.entities import AppointmentStatus, UpdateLog

def _city_slug(city: str) -> str:
    return '-'.join((city or '').strip().lower().split())

def run_ingestion(db: Session, provider_name: str = 'mock'):
    provider = MockProvider()
    records = provider.fetch_statuses()
    upserted = 0
    try:
        for rec in records:
            row = db.scalar(select(AppointmentStatus).where(
                AppointmentStatus.country==rec.country,
                AppointmentStatus.city==rec.city,
                AppointmentStatus.visa_type==rec.visa_type,
            ))
            if row:
                row.availability_status = rec.availability_status
                row.freshness_label = rec.freshness_label
                row.country_code = rec.country
                row.city_slug = _city_slug(rec.city)
            else:
                payload = rec.__dict__.copy()
                payload['country_code'] = rec.country
                payload['city_slug'] = _city_slug(rec.city)
                db.add(AppointmentStatus(**payload))
            upserted += 1
        db.add(UpdateLog(provider=provider.name, status='success', records_upserted=upserted))
        db.commit()
        return {"success": True, "data": {"upserted": upserted, "provider": provider.name}}
    except Exception as e:
        db.rollback()
        db.add(UpdateLog(provider=provider.name, status='failed', records_upserted=0, error_summary=str(e)))
        db.commit()
        return {"success": False, "error": "ingestion_failed"}
