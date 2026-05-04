import uuid
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, func, Index, JSON, UUID
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
    
    # Sprint 2: Trust & Report Stats
    trust_score: Mapped[int] = mapped_column(Integer, default=0)
    reports_submitted: Mapped[int] = mapped_column(Integer, default=0)
    reports_accepted: Mapped[int] = mapped_column(Integer, default=0)
    reports_rejected: Mapped[int] = mapped_column(Integer, default=0)
    account_status: Mapped[str] = mapped_column(String(20), default='active') # active, shadow_banned
    
    # Sprint 4: Monetization
    subscription_type: Mapped[str] = mapped_column(String(20), default='free') # free, premium
    subscription_expiry: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    amount: Mapped[int] = mapped_column(Integer) # In smallest currency unit (e.g. paisa for INR)
    status: Mapped[str] = mapped_column(String(20)) # pending, completed, failed
    provider: Mapped[str] = mapped_column(String(50)) # razorpay
    order_id: Mapped[str | None] = mapped_column(String(255))
    payment_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SubscriptionRecord(Base):
    __tablename__ = 'subscriptions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    plan: Mapped[str] = mapped_column(String(20)) # premium
    start_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20)) # active, expired

class Slot(Base):
    __tablename__ = 'slots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    visa_type: Mapped[str] = mapped_column(String(100), index=True)
    slot_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    slot_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Sprint 3.5: Lifecycle & Quality
    first_seen_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    seen_count: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    last_checked: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SlotSnapshot(Base):
    __tablename__ = 'slot_snapshots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_data: Mapped[str] = mapped_column(Text)

class SlotReport(Base):
    __tablename__ = 'slot_reports'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    country: Mapped[str] = mapped_column(String(100))
    center: Mapped[str] = mapped_column(String(100))
    visa_type: Mapped[str] = mapped_column(String(100))
    slot_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    slot_time: Mapped[str] = mapped_column(String(50))
    reported_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    screenshot_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String(20), default='pending') # pending, valid, rejected
    fingerprint_hash: Mapped[str] = mapped_column(String(128), index=True)

class SlotEvent(Base):
    __tablename__ = 'slot_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    visa_type: Mapped[str] = mapped_column(String(100), index=True)
    slot_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True))
    time_window: Mapped[str] = mapped_column(String(50))
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    sources_count: Mapped[int] = mapped_column(Integer, default=1)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    fingerprint_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)

class SlotHistory(Base):
    __tablename__ = 'slot_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True)
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence: Mapped[int] = mapped_column(Integer, default=0)

class SlotPattern(Base):
    __tablename__ = 'slot_patterns'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    center: Mapped[str] = mapped_column(String(100), index=True)
    peak_start_time: Mapped[str] = mapped_column(String(20)) # e.g. "14:00"
    peak_end_time: Mapped[str] = mapped_column(String(20)) # e.g. "16:00"
    confidence_score: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SessionRecord(Base):
    __tablename__ = 'session_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(50)) # e.g. "France TLS"
    session_id: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reuse_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AlertPreference(Base):
    __tablename__ = 'alert_preferences'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    country: Mapped[str] = mapped_column(String(100))
    center: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    origin: Mapped[str] = mapped_column(String(2))
    destination: Mapped[str] = mapped_column(String(2))
    visa_type: Mapped[str] = mapped_column(String(40), default='TOURIST')
    travel_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='DRAFT')
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

class VisaRoute(Base):
    __tablename__ = 'visa_routes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

class DataSource(Base):
    __tablename__ = 'data_sources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    terms_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

class AppointmentStatus(Base):
    __tablename__ = 'appointment_status'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    availability_status: Mapped[str] = mapped_column(String(40))
    freshness_label: Mapped[str] = mapped_column(String(40), default='last_known')
    country_code: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    city_slug: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey('data_sources.id'), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=100)
    last_checked: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    next_available_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (Index('ix_status_lookup', 'country', 'city', 'visa_type'),)

class AppointmentStatusHistory(Base):
    __tablename__ = 'appointment_status_history'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status_id: Mapped[int] = mapped_column(ForeignKey('appointment_status.id'), index=True)
    old_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40))
    old_next_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    new_next_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    changed_by: Mapped[str | None] = mapped_column(String(120))
    changed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UpdateLog(Base):
    __tablename__ = 'update_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(20))
    records_upserted: Mapped[int] = mapped_column(Integer, default=0)
    route_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default='system') # 'admin' or 'system'
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

class AdminStats(Base):
    __tablename__ = 'admin_stats'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    total_updates: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PortalMapping(Base):
    __tablename__ = 'portal_mappings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    city_slug: Mapped[str] = mapped_column(String(120), index=True)
    provider: Mapped[str] = mapped_column(String(120))
    portal_url: Mapped[str] = mapped_column(String(500))
    instructions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    portal_status: Mapped[str] = mapped_column(String(20), default='reachable')
    last_health_checked: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
