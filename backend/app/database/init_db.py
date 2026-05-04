from .session import engine, SessionLocal
from .base import Base
from ..models import entities  # noqa
from ..models.entities import AppointmentStatus, DataSource, User
from ..core.security import get_password_hash
from datetime import datetime, timezone
from sqlalchemy import select
import os

def init_db():
    # If on Vercel and DB exists, skip initialization to avoid read-only errors
    # The DB is pre-seeded and committed to the repository
    db_file = engine.url.database
    if os.environ.get("VERCEL") and db_file and os.path.exists(db_file):
        print("Using pre-seeded database on Vercel.")
        return

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")
        return
    
    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin_email = "admin@vixa.online"
        existing_admin = db.scalar(select(User).where(User.email == admin_email))
        if not existing_admin:
            admin = User(
                email=admin_email,
                name="Vixa Admin",
                password_hash=get_password_hash("vixa_admin_2026"),
                role='admin',
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Admin user seeded.")

        # 2. Seed Mock Data
        if db.query(AppointmentStatus).count() == 0:
            try:
                source = DataSource(name="Mock Provider", source_type="mock", active=True)
                db.add(source)
                db.commit()
                
                slots = [
                    AppointmentStatus(country="FR", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                    AppointmentStatus(country="ES", city="London", visa_type="TOURIST", availability_status="LIMITED", freshness_label="2h ago", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                    AppointmentStatus(country="IT", city="Manchester", visa_type="TOURIST", availability_status="NONE", freshness_label="1d ago", country_code="GB", city_slug="manchester", last_updated=datetime.now(timezone.utc)),
                    AppointmentStatus(country="DE", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                ]
                db.add_all(slots)
                db.commit()
                print("Mock data seeded.")
            except Exception as e:
                print(f"Warning: Could not seed data: {e}")
                db.rollback()
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()
