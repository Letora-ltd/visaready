from .session import engine, SessionLocal
from .base import Base
from ..models import entities  # noqa
from ..models.entities import AppointmentStatus, DataSource
from datetime import datetime, timezone

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if we have data
        if db.query(AppointmentStatus).count() == 0:
            # Add a mock data source
            source = DataSource(name="Mock Provider", source_type="mock", active=True)
            db.add(source)
            db.commit()
            
            # Add some mock slots
            slots = [
                AppointmentStatus(country="FR", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                AppointmentStatus(country="ES", city="London", visa_type="TOURIST", availability_status="LIMITED", freshness_label="2h ago", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                AppointmentStatus(country="IT", city="Manchester", visa_type="TOURIST", availability_status="NONE", freshness_label="1d ago", country_code="GB", city_slug="manchester", last_updated=datetime.now(timezone.utc)),
                AppointmentStatus(country="DE", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
            ]
            db.add_all(slots)
            db.commit()
    finally:
        db.close()
