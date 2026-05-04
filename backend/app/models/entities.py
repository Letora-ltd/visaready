from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, Integer, func, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..database.base import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default='user')
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    origin: Mapped[str] = mapped_column(String(2))
    destination: Mapped[str] = mapped_column(String(2))
    visa_type: Mapped[str] = mapped_column(String(40), default='TOURIST')
    travel_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='DRAFT')
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class VisaRoute(Base):
    __tablename__ = 'visa_routes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(2), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    visa_type: Mapped[str] = mapped_column(String(40), index=True)

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
    freshness_label: Mapped[str] = mapped_column(String(40), default='last_known')
    country_code: Mapped[str | None] = mapped_column(String(2), index=True, nullable=True)
    city_slug: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey('data_sources.id'), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_checked: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    __table_args__ = (Index('ix_status_lookup', 'country', 'city', 'visa_type'),)

class UpdateLog(Base):
    __tablename__ = 'update_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(20))
    records_upserted: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


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
