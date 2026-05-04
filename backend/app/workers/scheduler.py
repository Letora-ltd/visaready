from apscheduler.schedulers.background import BackgroundScheduler
from ..database.session import SessionLocal
from .ingest import run_ingestion
from ..core.config import settings
from ..models.entities import VisaRoute
from sqlalchemy import select

scheduler = BackgroundScheduler()


def start_scheduler():
    db = SessionLocal()
    try:
        routes = db.scalars(select(VisaRoute)).all()
    finally:
        db.close()

    if not routes:
        scheduler.add_job(lambda: _run(None), 'interval', minutes=settings.checker_interval_minutes, max_instances=1, coalesce=True, id='default-safe-check')
    else:
        for r in routes:
            interval = r.check_interval_minutes or settings.checker_interval_minutes
            scheduler.add_job(lambda c=r.country, ci=r.city, v=r.visa_type: _run({"country": c, "city": ci, "visa_type": v}), 'interval', minutes=interval, max_instances=1, coalesce=True, id=f'route-{r.id}')
    scheduler.start()


def _run(route_filter: dict | None):
    db = SessionLocal()
    try:
        run_ingestion(db, provider_name='safe_public')
    finally:
        db.close()
