from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
from ..database.session import get_db
from ..models.entities import Application, AppointmentStatus
from ..core.security import decode_jwt
from sqlalchemy import select

router = APIRouter(prefix='/api', tags=['api'])

def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    return decode_jwt(token)

class ApplicationIn(BaseModel):
    origin: str
    destination: str
    visa_type: str = "TOURIST"
    travel_date: str | None = None

@router.get('/applications')
def list_applications(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Application).where(Application.user_id == user["id"])).all()
    return rows

@router.post('/applications')
def create_application(payload: ApplicationIn, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    app = Application(
        id=str(uuid.uuid4())[:8].upper(),
        user_id=user["id"],
        origin=payload.origin,
        destination=payload.destination,
        visa_type=payload.visa_type,
        travel_date=payload.travel_date,
        status='DRAFT'
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app

@router.get('/visas/search')
def search_visas(origin: str, q: str = "", db: Session = Depends(get_db)):
    # This is a mock search for now, returning matching status entries
    query = select(AppointmentStatus).where(AppointmentStatus.country_code == origin.upper())
    if q:
        query = query.where(AppointmentStatus.city.ilike(f"%{q}%"))
    
    rows = db.scalars(query).all()
    # Format to match frontend expected corridor structure
    return [{"origin": origin, "dest": r.country, "destination_name": r.city, "visa_type": r.visa_type} for r in rows]
