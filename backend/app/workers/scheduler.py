from apscheduler.schedulers.background import BackgroundScheduler
from ..database.session import SessionLocal
from .ingest import run_ingestion

scheduler = BackgroundScheduler()

def start_scheduler():
    def job():
        db = SessionLocal()
        try:
            run_ingestion(db)
        finally:
            db.close()
    scheduler.add_job(job, 'interval', minutes=30, max_instances=1, coalesce=True)
    scheduler.start()
