import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, func, Index, JSON, UUID, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default='user')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Stats
    trust_score: Mapped[int] = mapped_column(Integer, default=0)
    reports_submitted: Mapped[int] = mapped_column(Integer, default=0)
    reports_accepted: Mapped[int] = mapped_column(Integer, default=0)
    reports_rejected: Mapped[int] = mapped_column(Integer, default=0)
    account_status: Mapped[str] = mapped_column(String(20), default='active')
    
    # Monetization & Engagement
    subscription_type: Mapped[str] = mapped_column(String(20), default='free')
    subscription_expiry: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_code: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(50))
    order_id: Mapped[str | None] = mapped_column(String(255))
    payment_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SubscriptionRecord(Base):
    __tablename__ = 'subscriptions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    plan: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))

class Slot(Base):
    __tablename__ = 'slots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    visa_type: Mapped[str] = mapped_column(String(100), index=True)
    slot_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slot_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hour: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

class ProcessedStripeEvent(Base):
    __tablename__ = 'processed_stripe_events'
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserDailyStats(Base):
    __tablename__ = 'user_daily_stats'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    slots_found: Mapped[int] = mapped_column(Integer, default=0)
    alerts_sent: Mapped[int] = mapped_column(Integer, default=0)
    prompts_shown: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint('user_id', 'date', name='uq_user_date_stats'),)

class ConversionLog(Base):
    __tablename__ = 'conversion_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user_id')) # Fix: should be user_id field
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    trigger_type: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Referral(Base):
    __tablename__ = 'referrals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    referred_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), unique=True)
    status: Mapped[str] = mapped_column(String(20), default='joined') # joined, rewarded
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AlertPreference(Base):
    __tablename__ = 'alert_preferences'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    country: Mapped[str] = mapped_column(String(100))
    center: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'center', name='uq_user_center_alert'),)
