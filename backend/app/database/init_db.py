import json
from sqlalchemy import select
from .session import engine, SessionLocal
from .base import Base
from ..models import entities  # noqa
from ..models.entities import VisaPortal


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seeds = [
            ("FR", "London", "TOURIST", "TLScontact", "https://fr.tlscontact.com/gb/lon/index.php", ["Login to official portal manually", "Open Appointments section", "Select London center", "Check earliest available date"]),
            ("FR", "Manchester", "TOURIST", "TLScontact", "https://fr.tlscontact.com/gb/man/index.php", ["Login to official portal manually", "Open Appointments section", "Select Manchester center", "Check earliest available date"]),
            ("ES", "London", "TOURIST", "BLS Spain Visa", "https://uk.blsspainvisa.com/london/", ["Open official BLS portal", "Navigate to appointment booking info", "Select London jurisdiction", "Verify earliest appointment indicator"]),
            ("DE", "London", "TOURIST", "VFS Global", "https://visa.vfsglobal.com/gbr/en/deu", ["Open official VFS portal", "Go to appointment availability", "Select London center", "Record earliest visible appointment date"]),
        ]
        for country, city, visa_type, provider, url, steps in seeds:
            exists = db.scalar(select(VisaPortal).where(VisaPortal.country==country, VisaPortal.city==city, VisaPortal.visa_type==visa_type))
            if not exists:
                db.add(VisaPortal(country=country, city=city, visa_type=visa_type, provider=provider, portal_url=url, instructions=json.dumps(steps)))
        db.commit()
    finally:
        db.close()
