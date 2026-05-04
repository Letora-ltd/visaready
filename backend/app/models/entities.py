from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class VisaRoute(Base):
    __tablename__ = 'visa_routes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)

class DataSource(Base):
    __tablename__ = 'data_sources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    terms_url: Mapped[str | None] = mapped_column(String(400), nullable=True)

class AppointmentStatus(Base):
    __tablename__ = 'appointment_status'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    availability_status: Mapped[str] = mapped_column(String(40))
    next_available_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness_label: Mapped[str] = mapped_column(String(40), default='last_known')
    source_type: Mapped[str] = mapped_column(String(20), default='fallback')
    source_id: Mapped[int | None] = mapped_column(ForeignKey('data_sources.id'), nullable=True)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    __table_args__ = (Index('ix_status_lookup', 'country', 'city', 'visa_type'),)

class AdminTask(Base):
    __tablename__ = 'admin_tasks'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)
    task_type: Mapped[str] = mapped_column(String(20), default='verify')
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    status: Mapped[str] = mapped_column(String(20), default='pending', index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class UpdateLog(Base):
    __tablename__ = 'update_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(20))
    records_upserted: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(120), index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    target_key: Mapped[str] = mapped_column(String(255), index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
