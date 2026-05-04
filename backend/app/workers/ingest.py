from sqlalchemy.orm import Session
from ..integrations.providers import MockProvider, SafePublicProvider
from ..models.entities import UpdateLog
from ..services.visa_service import upsert_status
from ..services.notification_service import notify


def run_ingestion(db: Session, provider_name: str = 'mock'):
    provider = SafePublicProvider() if provider_name == 'safe_public' else MockProvider()
    upserted = 0
    try:
        records = provider.fetch_statuses()
        for rec in records:
            _, changed = upsert_status(db, rec.__dict__, actor=provider.name, source_type=provider.source_type)
            if changed:
                upserted += 1
        db.add(UpdateLog(provider=provider.name, status='success', records_upserted=upserted))
        db.commit()
        return {"success": True, "data": {"upserted": upserted, "provider": provider.name}}
    except Exception as e:
        db.rollback()
        db.add(UpdateLog(provider=provider.name, status='failed', records_upserted=0, error_summary=str(e)))
        db.commit()
        notify("update_failed", "Automated update failed", {"provider": provider.name, "error": str(e)})
        return {"success": False, "error": "ingestion_failed"}
