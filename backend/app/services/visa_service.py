from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models.entities import VisaRoute, AppointmentStatus

def list_routes(db: Session):
    rows = db.scalars(select(VisaRoute)).all()
    return [{"country": r.country, "city": r.city, "visa_type": r.visa_type} for r in rows]

def get_status(db: Session, origin: str, destination: str | None):
    q = select(AppointmentStatus).where(AppointmentStatus.country_code == origin.upper())
    if destination:
        q = q.where(AppointmentStatus.country == destination.upper())
    rows = db.scalars(q).all()
    return rows

def last_updated(db: Session):
    return db.scalar(select(func.max(AppointmentStatus.last_updated)))
