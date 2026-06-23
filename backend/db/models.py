"""ORM models - User, EnrollmentSample, RecognitionLog."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("name", "hand", name="uq_users_name_hand"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    hand: Mapped[str] = mapped_column(String(8), nullable=False)
    template_embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    samples: Mapped[list["EnrollmentSample"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    logs: Mapped[list["RecognitionLog"]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )


class EnrollmentSample(Base):
    __tablename__ = "enrollment_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="samples")


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # "verify"|"identify"
    claimed_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    matched_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    similarity: Mapped[float] = mapped_column(Float, nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="logs")


class Account(Base):
    """Registered platform user (email login + palm biometrics)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), default="employee", nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_sub: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    left_template: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    right_template: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    activities: Mapped[list["ActivityLog"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EmailVerificationCode(Base):
    """One-time email verification code for signup."""

    __tablename__ = "email_verification_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    account: Mapped["Account"] = relationship()


class PasswordResetCode(Base):
    """One-time password reset code."""

    __tablename__ = "password_reset_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    account: Mapped["Account"] = relationship()


class AttendanceRecord(Base):
    """One row per employee per calendar work day."""

    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("account_id", "work_date", name="uq_attendance_account_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="present")
    first_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    session_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    marked_by: Mapped[str] = mapped_column(String(16), default="system", nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="attendance_records")


class EmployeeInvite(Base):
    """HR-issued signup invite (one-time link)."""

    __tablename__ = "employee_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    invited_by_account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CompanySettings(Base):
    """Singleton company attendance policy (id=1)."""

    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_day_start: Mapped[str] = mapped_column(String(5), default="09:00", nullable=False)
    grace_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    require_palm_logout: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    exclude_weekends: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    half_day_hours: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    notify_absent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notify_weekly_summary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_notify_email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)


class CompanyHoliday(Base):
    """Company-wide non-working day."""

    __tablename__ = "company_holidays"
    __table_args__ = (UniqueConstraint("holiday_date", name="uq_holiday_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)


class AuthSession(Base):
    """Login session for employee time-on-app tracking."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    login_method: Mapped[str] = mapped_column(String(16), nullable=False)  # email | palm | signup
    logout_method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    attendance_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("attendance_records.id", ondelete="SET NULL"), nullable=True
    )
    login_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False, index=True)
    logout_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    account: Mapped["Account"] = relationship(back_populates="sessions")


class ActivityLog(Base):
    """Per-employee activity audit trail."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    detail: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False, index=True)

    account: Mapped[Optional["Account"]] = relationship(back_populates="activities")


class TrainingIngestLog(Base):
    """Tracks live captures copied into the training corpus."""

    __tablename__ = "training_ingest_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    dest_path: Mapped[str] = mapped_column(String(512), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    hand: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False, index=True)


class TrainingRun(Base):
    """Weekly / manual model retraining job record."""

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    trigger: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    images_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    val_eer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val_rank1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checkpoint_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
