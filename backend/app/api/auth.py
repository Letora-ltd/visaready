from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from ..database.session import get_db
from ..models.entities import User
from ..core.security import create_access_token, get_password_hash, verify_password, decode_jwt
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer

from ..core.logging import logger
import logging

router = APIRouter(prefix='/api/auth', tags=['auth'])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post('/login')
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")
