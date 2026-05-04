from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
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
    telegram_chat_id: str | None = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post('/register')
async def register(payload: SignupIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        email=payload.email,
        name=payload.name,
        telegram_chat_id=payload.telegram_chat_id,
        password_hash=get_password_hash(payload.password),
        role='user',
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": user.email, "id": str(user.id), "role": user.role})
    return {
        "token": token, 
        "role": user.role,
        "user": {
            "id": str(user.id), 
            "email": user.email, 
            "name": user.name,
            "telegram_chat_id": user.telegram_chat_id
        }
    }

@router.post('/login')
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    
    token = create_access_token({"sub": user.email, "id": str(user.id), "role": user.role})
    return {
        "token": token, 
        "role": user.role,
        "user": {
            "id": str(user.id), 
            "email": user.email, 
            "name": user.name,
            "telegram_chat_id": user.telegram_chat_id
        }
    }
