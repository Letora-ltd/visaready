from .session import engine, AsyncSessionLocal
from .base import Base
from ..models import entities  # noqa
from ..models.entities import AppointmentStatus, DataSource, User
from ..core.security import get_password_hash
from datetime import datetime, timezone
from sqlalchemy import select
import os

async def init_db():
    # 1. Create tables
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Warning: Could not create tables: {e}")
            # We continue because tables might already exist
    
    async with AsyncSessionLocal() as db:
        try:
            # 2. Seed Admin User
            admin_email = "admin@vixa.online"
            result = await db.execute(select(User).where(User.email == admin_email))
            existing_admin = result.scalar_one_or_none()
            if not existing_admin:
                admin = User(
                    email=admin_email,
                    name="Vixa Admin",
                    password_hash=get_password_hash("vixa_admin_2026"),
                    role='admin',
                    is_active=True
                )
                db.add(admin)
                await db.commit()
                print("Admin user seeded.")

            # 3. Seed Mock Data if empty
            status_count_res = await db.execute(select(AppointmentStatus))
            if len(status_count_res.scalars().all()) == 0:
                try:
                    source = DataSource(name="Mock Provider", source_type="mock", active=True)
                    db.add(source)
                    await db.commit()
                    
                    slots = [
                        AppointmentStatus(country="FR", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                        AppointmentStatus(country="ES", city="London", visa_type="TOURIST", availability_status="LIMITED", freshness_label="2h ago", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                        AppointmentStatus(country="IT", city="Manchester", visa_type="TOURIST", availability_status="NONE", freshness_label="1d ago", country_code="GB", city_slug="manchester", last_updated=datetime.now(timezone.utc)),
                        AppointmentStatus(country="DE", city="London", visa_type="TOURIST", availability_status="AVAILABLE", freshness_label="Live", country_code="GB", city_slug="london", last_updated=datetime.now(timezone.utc)),
                    ]
                    db.add_all(slots)
                    await db.commit()
                    print("Mock data seeded.")
                except Exception as e:
                    print(f"Warning: Could not seed data: {e}")
                    await db.rollback()
        except Exception as e:
            print(f"Error querying database: {e}")
        finally:
            await db.close()
