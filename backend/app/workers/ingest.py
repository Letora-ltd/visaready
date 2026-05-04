from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..integrations.providers import MockProvider
from ..models.entities import AppointmentStatus, UpdateLog, AppointmentStatusHistory
from ..core.logic import calculate_confidence

def _city_slug(city: str) -> str:
    return '-'.join((city or '').strip().lower().split())

def run_ingestion(db: Session, provider_name: str = 'mock'):
    provider = MockProvider()
    records = provider.fetch_statuses()
    upserted = 0
    now = datetime.now(timezone.utc)
    try:
        for rec in records:
            row = db.scalar(select(AppointmentStatus).where(
                AppointmentStatus.country==rec.country,
                AppointmentStatus.city==rec.city,
                AppointmentStatus.visa_type==rec.visa_type,
            ))
            if row:
                # Capture history if status changed
                if row.availability_status != rec.availability_status:
                    db.add(AppointmentStatusHistory(
                        status_id=row.id,
                        old_status=row.availability_status,
                        new_status=rec.availability_status,
                        old_next_date=row.next_available_date,
                        new_next_date=None, # System updates might not have this
                        changed_by=f"system_{provider.name}"
                    ))
                    row.last_updated = now
                
                row.availability_status = rec.availability_status
                row.freshness_label = rec.freshness_label
                row.country_code = rec.country
                row.city_slug = _city_slug(rec.city)
                row.verified_by = f"system_{provider.name}"
                row.confidence_score = calculate_confidence(row.last_updated, 'system')
                row.version += 1
            else:
                payload = rec.__dict__.copy()
                payload['country_code'] = rec.country
                payload['city_slug'] = _city_slug(rec.city)
                payload['verified_by'] = f"system_{provider.name}"
                payload['last_updated'] = now
                payload['last_checked'] = now
                payload['confidence_score'] = calculate_confidence(now, 'system')
                payload['version'] = 1
                
                new_row = AppointmentStatus(**payload)
                db.add(new_row)
                db.flush()
                
                db.add(AppointmentStatusHistory(
                    status_id=new_row.id,
                    old_status=None,
                    new_status=rec.availability_status,
                    old_next_date=None,
                    new_next_date=None,
                    changed_by=f"system_{provider.name}"
                ))
                
            upserted += 1
        
        db.add(UpdateLog(provider=provider.name, status='success', records_upserted=upserted, source='system'))
        db.commit()
        return {"success": True, "data": {"upserted": upserted, "provider": provider.name}}
    except Exception as e:
        db.rollback()
        db.add(UpdateLog(provider=provider.name, status='failed', records_upserted=0, source='system', error_summary=str(e)))
        db.commit()
        return {"success": False, "error": "ingestion_failed"}
