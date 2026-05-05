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

class SlotEvent(Base):
    __tablename__ = 'slot_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    visa_type: Mapped[str] = mapped_column(String(100), index=True)
    slot_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_window: Mapped[str | None] = mapped_column(String(100), nullable=True) # Renamed from slot_time to time_window for consistency
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SlotHistory(Base):
    __tablename__ = 'slot_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey('slot_events.id'))
    status: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SlotPattern(Base):
    __tablename__ = 'slot_patterns'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    hour: Mapped[int] = mapped_column(Integer)
    avg_confidence: Mapped[float] = mapped_column(Float)
    last_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True))

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

class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    origin: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    visa_type: Mapped[str] = mapped_column(String(100))
    travel_date: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))

class AppointmentStatus(Base):
    __tablename__ = 'appointment_status'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(10))
    city: Mapped[str] = mapped_column(String(100))
    visa_type: Mapped[str] = mapped_column(String(100))
    availability_status: Mapped[str] = mapped_column(String(100))
    freshness_label: Mapped[str] = mapped_column(String(100))
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)
    verified_by: Mapped[str | None] = mapped_column(String(100))
    # Added for admin support
    city_slug: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_available_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class PortalMapping(Base):
    __tablename__ = 'portal_mappings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    visa_type: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(String(10))
    city_slug: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))
    portal_url: Mapped[str] = mapped_column(Text)
    instructions: Mapped[dict | None] = mapped_column(JSON)
    portal_status: Mapped[str] = mapped_column(String(20), default='unknown')
    last_health_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[str | None] = mapped_column(String(100))

class AppointmentStatusHistory(Base):
    __tablename__ = 'appointment_status_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status_id: Mapped[int] = mapped_column(ForeignKey('appointment_status.id'))
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20))
    old_next_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_next_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    changed_by: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AdminStats(Base):
    __tablename__ = 'admin_stats'
    admin_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    total_updates: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UpdateLog(Base):
    __tablename__ = 'update_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    records_upserted: Mapped[int] = mapped_column(Integer, default=0)
    route_id: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SlotSnapshot(Base):
    __tablename__ = 'slot_snapshots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str | None] = mapped_column(String(100))
    center: Mapped[str] = mapped_column(String(100))
    raw_data: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SessionRecord(Base):
    __tablename__ = 'session_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    session_data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='active')
    reuse_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DataSource(Base):
    __tablename__ = 'data_sources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
