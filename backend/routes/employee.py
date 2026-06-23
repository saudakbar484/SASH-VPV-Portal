"""Employee self-service APIs — dashboard, attendance, activity."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.attendance import get_or_create_today_record, get_settings, work_date_str
from backend.db import models
from backend.deps import get_db
from backend.deps_auth import require_employee

router = APIRouter(prefix="/api/employee", tags=["employee"])


class TodaySessionInfo(BaseModel):
    session_id: Optional[int] = None
    login_at: Optional[datetime] = None
    is_active: bool = False


class EmployeeDashboardResponse(BaseModel):
    full_name: str
    work_date: str
    status: str
    first_login_at: Optional[datetime] = None
    total_seconds_today: int
    session_count: int
    is_online: bool
    active_session: Optional[TodaySessionInfo] = None
    work_day_start: str
    grace_minutes: int


class AttendanceDayEntry(BaseModel):
    work_date: str
    status: str
    first_login_at: Optional[datetime] = None
    last_logout_at: Optional[datetime] = None
    total_seconds: int
    session_count: int


class EmployeeAttendanceResponse(BaseModel):
    month: str
    records: list[AttendanceDayEntry]


class ActivityEntry(BaseModel):
    id: int
    event_type: str
    detail: Optional[str] = None
    created_at: datetime


class EmployeeActivityResponse(BaseModel):
    count: int
    activities: list[ActivityEntry]


class EmployeeProfileResponse(BaseModel):
    account_id: int
    email: str
    full_name: str
    dataset_id: str
    dataset_name: str
    role: str
    registered_at: datetime
    left_enrolled: bool
    right_enrolled: bool


class CompanyPolicyResponse(BaseModel):
    work_day_start: str
    grace_minutes: int
    timezone: str
    half_day_hours: float
    require_palm_logout: bool
    exclude_weekends: bool


class AttendanceMonthSummary(BaseModel):
    month: str
    total_days: int
    present: int
    late: int
    absent: int
    half_day: int
    leave: int
    total_seconds: int
    avg_seconds_per_day: int


@router.get("/dashboard", response_model=EmployeeDashboardResponse)
def employee_dashboard(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_employee),
) -> EmployeeDashboardResponse:
    settings = get_settings(db)
    wd = work_date_str(db)
    record = get_or_create_today_record(db, account.id, work_date=wd)
    active = db.execute(
        select(models.AuthSession).where(
            models.AuthSession.account_id == account.id,
            models.AuthSession.is_active.is_(True),
        )
    ).scalar_one_or_none()

    active_info = None
    if active:
        active_info = TodaySessionInfo(
            session_id=active.id,
            login_at=active.login_at,
            is_active=True,
        )

    status = record.status
    if record.first_login_at is None and not (active and active.is_active):
        status = "not_checked_in"

    return EmployeeDashboardResponse(
        full_name=account.full_name,
        work_date=wd,
        status=status,
        first_login_at=record.first_login_at,
        total_seconds_today=record.total_seconds or 0,
        session_count=record.session_count or 0,
        is_online=active is not None,
        active_session=active_info,
        work_day_start=settings.work_day_start,
        grace_minutes=settings.grace_minutes,
    )


@router.get("/attendance", response_model=EmployeeAttendanceResponse)
def employee_attendance(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_employee),
) -> EmployeeAttendanceResponse:
    prefix = month
    rows = db.execute(
        select(models.AttendanceRecord)
        .where(
            models.AttendanceRecord.account_id == account.id,
            models.AttendanceRecord.work_date.startswith(prefix),
        )
        .order_by(models.AttendanceRecord.work_date.desc())
    ).scalars().all()

    return EmployeeAttendanceResponse(
        month=month,
        records=[
            AttendanceDayEntry(
                work_date=r.work_date,
                status=r.status,
                first_login_at=r.first_login_at,
                last_logout_at=r.last_logout_at,
                total_seconds=r.total_seconds or 0,
                session_count=r.session_count or 0,
            )
            for r in rows
        ],
    )


@router.get("/activity", response_model=EmployeeActivityResponse)
def employee_activity(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_employee),
) -> EmployeeActivityResponse:
    rows = db.execute(
        select(models.ActivityLog)
        .where(models.ActivityLog.account_id == account.id)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(100)
    ).scalars().all()
    return EmployeeActivityResponse(
        count=len(rows),
        activities=[
            ActivityEntry(
                id=a.id,
                event_type=a.event_type,
                detail=a.detail,
                created_at=a.created_at,
            )
            for a in rows
        ],
    )


@router.get("/profile", response_model=EmployeeProfileResponse)
def employee_profile(
    account: models.Account = Depends(require_employee),
) -> EmployeeProfileResponse:
    return EmployeeProfileResponse(
        account_id=account.id,
        email=account.email,
        full_name=account.full_name,
        dataset_id=account.dataset_id,
        dataset_name=account.dataset_name,
        role=account.role,
        registered_at=account.created_at,
        left_enrolled=account.left_template is not None,
        right_enrolled=account.right_template is not None,
    )


@router.get("/company-policy", response_model=CompanyPolicyResponse)
def employee_company_policy(
    _: models.Account = Depends(require_employee),
    db: Session = Depends(get_db),
) -> CompanyPolicyResponse:
    s = get_settings(db)
    return CompanyPolicyResponse(
        work_day_start=s.work_day_start,
        grace_minutes=s.grace_minutes,
        timezone=s.timezone,
        half_day_hours=s.half_day_hours,
        require_palm_logout=s.require_palm_logout,
        exclude_weekends=s.exclude_weekends,
    )


@router.get("/attendance/summary", response_model=AttendanceMonthSummary)
def employee_attendance_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_employee),
) -> AttendanceMonthSummary:
    rows = db.execute(
        select(models.AttendanceRecord)
        .where(
            models.AttendanceRecord.account_id == account.id,
            models.AttendanceRecord.work_date.startswith(month),
        )
    ).scalars().all()
    counts: dict[str, int] = {}
    total_sec = 0
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
        total_sec += r.total_seconds or 0
    n = len(rows)
    return AttendanceMonthSummary(
        month=month,
        total_days=n,
        present=counts.get("present", 0),
        late=counts.get("late", 0),
        absent=counts.get("absent", 0),
        half_day=counts.get("half_day", 0),
        leave=counts.get("leave", 0),
        total_seconds=total_sec,
        avg_seconds_per_day=total_sec // n if n else 0,
    )
