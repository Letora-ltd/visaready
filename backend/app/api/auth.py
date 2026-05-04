from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database.session import get_db
from ..models.entities import User
from ..core.security import sign_jwt, get_password_hash, verify_password
from sqlalchemy import select

router = APIRouter(prefix='/auth', tags=['auth'])

class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    country_code: str = "GB"

class LoginIn(BaseModel):
    email: str
    password: str

@router.post('/signup')
def signup(payload: SignupIn, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=get_password_hash(payload.password),
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = sign_jwt({"sub": user.email, "id": user.id, "role": user.role})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}

@router.post('/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = sign_jwt({"sub": user.email, "id": user.id, "role": user.role})
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name}}
