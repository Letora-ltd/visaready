from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from ..database.session import get_db
from ..models.entities import User
from ..core.security import create_access_token, get_password_hash, verify_password
from sqlalchemy import select

router = APIRouter(prefix='/api/auth', tags=['auth'])

class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post('/register')
def register(payload: SignupIn, db: Session = Depends(get_db)):
    # role = user only for public registration
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=get_password_hash(payload.password),
        role='user',
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role})
    return {
        "token": token, 
        "role": user.role,
        "user": {"id": user.id, "email": user.email, "name": user.name}
    }

@router.post('/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    token = create_access_token({"sub": user.email, "id": user.id, "role": user.role})
    return {
        "token": token, 
        "role": user.role,
        "user": {"id": user.id, "email": user.email, "name": user.name}
    }
