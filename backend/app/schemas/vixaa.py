from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional, List

class UserCreate(BaseModel):
    email: EmailStr
    telegram_chat_id: Optional[str] = None

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    telegram_chat_id: Optional[str]

    class Config:
        from_attributes = True

class AlertPreferenceCreate(BaseModel):
    user_id: UUID
    country: str
    center: str

class SlotRead(BaseModel):
    id: int
    country: str
    center: str
    visa_type: str
    slot_date: Optional[datetime]
    slot_time: Optional[str]
    last_checked: datetime

    class Config:
        from_attributes = True

class SlotReportCreate(BaseModel):
    country: str
    center: str
    visa_type: str
    slot_date: datetime
    slot_time: str
    screenshot_url: Optional[str] = None

class SlotEventRead(BaseModel):
    id: int
    country: str
    center: str
    visa_type: str
    slot_date: datetime
    time_window: str
    confidence_score: int
    sources_count: int
    last_updated: datetime

    class Config:
        from_attributes = True

class RecommendationRead(BaseModel):
    peak_time_window: str
    confidence_score: int
    recommendation_message: str

class HistoryItem(BaseModel):
    date: datetime
    total_events: int
    avg_confidence: int

class HistoryRead(BaseModel):
    country: str
    center: str
    history: List[HistoryItem]

class DashboardRead(BaseModel):
    preferences: List[AlertPreferenceCreate]
    recent_events: List[SlotEventRead]
    recommendations: List[RecommendationRead]
    history_summary: Optional[HistoryRead] = None
