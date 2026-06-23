"""Admin-only APIs — employees, analytics, registered identities."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime, timedelta, timezone
from io import StringIO
import csv
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.attendance import (
    add_holiday,
    close_day_absences,
    delete_holiday,
    get_settings,
    list_attendance_report,
    list_holidays,
    override_attendance,
    update_settings,
    work_date_str,
)
from backend.auth.folder_mapping import read_rows
from backend.auth.invites import create_invite, revoke_invite
from backend.auth.notifications import (
    get_primary_admin_email,
    resolve_admin_notify_email,
    send_test_email,
    send_weekly_summary,
    smtp_configured,
)
from backend.settings import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD
from backend.auth.template_cache import refresh_account_templates
from backend.db import models
from backend.deps import get_db
from backend.deps_auth import get_current_account
from backend.settings import DATASET_DIR, USERS_REF_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(account: models.Account = Depends(get_current_account)) -> models.Account:
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return account


class HandInfo(BaseModel):
    hand: Literal["Left", "Right"]
    user_id: Optional[int] = None
    sample_count: int = 0
    enrolled: bool = False


class RegisteredIdentity(BaseModel):
    account_id: int
    full_name: str
    email: str
    dataset_id: str
    dataset_name: str
    role: str
    registered_at: datetime
    hands: list[HandInfo]
    total_samples: int


class RegisteredIdentitiesResponse(BaseModel):
    count: int
    identities: list[RegisteredIdentity]


class DatasetFolderHand(BaseModel):
    hand: str
    image_count: int
    files: list[str]


class DatasetRegistryEntry(BaseModel):
    folder_id: str
    dataset_name: str
    email: str
    full_name: str
    account_id: int
    hands: list[DatasetFolderHand]


class DatasetRegistryResponse(BaseModel):
    count: int
    entries: list[DatasetRegistryEntry]


class EmployeeSummary(BaseModel):
    account_id: int
    full_name: str
    email: str
    dataset_id: str
    role: str
    registered_at: datetime
    total_sessions: int
    total_time_seconds: int
    last_login_at: Optional[datetime] = None
    is_online: bool
    activity_count: int
    today_status: Optional[str] = None
    today_seconds: int = 0


class EmployeesListResponse(BaseModel):
    count: int
    employees: list[EmployeeSummary]


class ActivityEntry(BaseModel):
    id: int
    event_type: str
    detail: Optional[str] = None
    created_at: datetime


class SessionEntry(BaseModel):
    id: int
    login_method: str
    login_at: datetime
    logout_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_active: bool


class EmployeeDetailResponse(BaseModel):
    account_id: int
    full_name: str
    email: str
    dataset_id: str
    dataset_name: str
    role: str
    registered_at: datetime
    total_time_seconds: int
    sessions: list[SessionEntry]
    activities: list[ActivityEntry]
    recognition_events: int


class TimeSeriesPoint(BaseModel):
    label: str
    count: int


class LogsAnalyticsResponse(BaseModel):
    total_recognition: int
    accepted: int
    rejected: int
    total_logins: int
    active_sessions: int
    recognition_by_day: list[TimeSeriesPoint]
    activity_by_type: list[TimeSeriesPoint]
    events_by_employee: list[TimeSeriesPoint]


class DeleteEmployeeResponse(BaseModel):
    success: bool
    deleted_account_id: int
    deleted_users: int


def _hand_info(db: Session, dataset_name: str) -> list[HandInfo]:
    hands: list[HandInfo] = []
    for hand in ("Left", "Right"):
        user = db.execute(
            select(models.User).where(
                models.User.name == dataset_name,
                models.User.hand == hand,
            )
        ).scalar_one_or_none()
        if user:
            hands.append(
                HandInfo(
                    hand=hand,  # type: ignore[arg-type]
                    user_id=user.id,
                    sample_count=len(user.samples),
                    enrolled=True,
                )
            )
        else:
            hands.append(HandInfo(hand=hand, sample_count=0, enrolled=False))  # type: ignore[arg-type]
    return hands


def _count_images(folder_id: str, hand: str) -> tuple[int, list[str]]:
    hand_dir = DATASET_DIR / folder_id / hand
    if not hand_dir.is_dir():
        return 0, []
    files = sorted(p.name for p in hand_dir.glob("*.png"))
    return len(files), files


@router.get("/registered-identities", response_model=RegisteredIdentitiesResponse)
def list_registered_identities(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> RegisteredIdentitiesResponse:
    accounts = db.execute(
        select(models.Account).order_by(models.Account.created_at.desc())
    ).scalars().all()
    items: list[RegisteredIdentity] = []
    for acc in accounts:
        hands = _hand_info(db, acc.dataset_name)
        items.append(
            RegisteredIdentity(
                account_id=acc.id,
                full_name=acc.full_name,
                email=acc.email,
                dataset_id=acc.dataset_id,
                dataset_name=acc.dataset_name,
                role=acc.role,
                registered_at=acc.created_at,
                hands=hands,
                total_samples=sum(h.sample_count for h in hands),
            )
        )
    return RegisteredIdentitiesResponse(count=len(items), identities=items)


@router.get("/dataset-registry", response_model=DatasetRegistryResponse)
def dataset_registry(
    _: models.Account = Depends(require_admin),
) -> DatasetRegistryResponse:
    entries: list[DatasetRegistryEntry] = []
    for row in read_rows():
        fid = row.get("folder_id", "")
        hands: list[DatasetFolderHand] = []
        for hand in ("Left", "Right"):
            n, files = _count_images(fid, hand)
            hands.append(DatasetFolderHand(hand=hand, image_count=n, files=files))
        entries.append(
            DatasetRegistryEntry(
                folder_id=fid,
                dataset_name=row.get("dataset_name", ""),
                email=row.get("email", ""),
                full_name=row.get("full_name", ""),
                account_id=int(row.get("account_id", 0) or 0),
                hands=hands,
            )
        )
    return DatasetRegistryResponse(count=len(entries), entries=entries)


@router.get("/employees", response_model=EmployeesListResponse)
def list_employees(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> EmployeesListResponse:
    accounts = db.execute(
        select(models.Account)
        .where(models.Account.role == "employee")
        .order_by(models.Account.full_name)
    ).scalars().all()
    summaries: list[EmployeeSummary] = []
    today = work_date_str(db)
    for acc in accounts:
        sessions = list(acc.sessions)
        total_time = sum(s.duration_seconds or 0 for s in sessions if s.duration_seconds)
        active = any(s.is_active for s in sessions)
        last_login = max((s.login_at for s in sessions), default=None)
        act_count = len(acc.activities)
        att = db.execute(
            select(models.AttendanceRecord).where(
                models.AttendanceRecord.account_id == acc.id,
                models.AttendanceRecord.work_date == today,
            )
        ).scalar_one_or_none()
        today_status: Optional[str] = None
        today_seconds = 0
        if att:
            today_status = att.status if att.first_login_at else None
            today_seconds = att.total_seconds or 0
        if active:
            today_status = today_status or "online"
        summaries.append(
            EmployeeSummary(
                account_id=acc.id,
                full_name=acc.full_name,
                email=acc.email,
                dataset_id=acc.dataset_id,
                role=acc.role,
                registered_at=acc.created_at,
                total_sessions=len(sessions),
                total_time_seconds=total_time,
                last_login_at=last_login,
                is_online=active,
                activity_count=act_count,
                today_status=today_status,
                today_seconds=today_seconds,
            )
        )
    return EmployeesListResponse(count=len(summaries), employees=summaries)


@router.get("/employees/{account_id}", response_model=EmployeeDetailResponse)
def get_employee_detail(
    account_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> EmployeeDetailResponse:
    acc = db.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Employee not found")

    sessions = sorted(acc.sessions, key=lambda s: s.login_at, reverse=True)
    activities = sorted(acc.activities, key=lambda a: a.created_at, reverse=True)[:100]
    rec_count = db.execute(
        select(func.count(models.RecognitionLog.id)).where(
            models.RecognitionLog.matched_name == acc.dataset_name
        )
    ).scalar_one()

    return EmployeeDetailResponse(
        account_id=acc.id,
        full_name=acc.full_name,
        email=acc.email,
        dataset_id=acc.dataset_id,
        dataset_name=acc.dataset_name,
        role=acc.role,
        registered_at=acc.created_at,
        total_time_seconds=sum(s.duration_seconds or 0 for s in sessions),
        sessions=[
            SessionEntry(
                id=s.id,
                login_method=s.login_method,
                login_at=s.login_at,
                logout_at=s.logout_at,
                duration_seconds=s.duration_seconds,
                is_active=s.is_active,
            )
            for s in sessions
        ],
        activities=[
            ActivityEntry(
                id=a.id,
                event_type=a.event_type,
                detail=a.detail,
                created_at=a.created_at,
            )
            for a in activities
        ],
        recognition_events=int(rec_count),
    )


@router.delete("/employees/{account_id}", response_model=DeleteEmployeeResponse)
def delete_employee(
    account_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> DeleteEmployeeResponse:
    acc = db.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Employee not found")
    if acc.role == "admin":
        admin_count = db.execute(
            select(func.count()).select_from(models.Account).where(models.Account.role == "admin")
        ).scalar_one()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the only admin account")

    deleted_users = 0
    for hand in ("Left", "Right"):
        user = db.execute(
            select(models.User).where(
                models.User.name == acc.dataset_name,
                models.User.hand == hand,
            )
        ).scalar_one_or_none()
        if user:
            user_dir = USERS_REF_DIR / str(user.id)
            if user_dir.exists():
                shutil.rmtree(user_dir, ignore_errors=True)
            db.delete(user)
            deleted_users += 1

    dataset_dir = DATASET_DIR / acc.dataset_id
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir, ignore_errors=True)

    from backend.auth.folder_mapping import ensure_csv
    import csv
    from backend.settings import FOLDER_MAPPING_CSV

    ensure_csv()
    rows = read_rows()
    with FOLDER_MAPPING_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["folder_id", "dataset_name", "email", "full_name", "account_id"])
        for row in rows:
            if str(row.get("account_id")) == str(account_id):
                continue
            writer.writerow([
                row.get("folder_id"),
                row.get("dataset_name"),
                row.get("email"),
                row.get("full_name"),
                row.get("account_id"),
            ])

    db.delete(acc)
    db.commit()
    refresh_account_templates(db)

    logger.info("Deleted employee account_id=%s users=%s", account_id, deleted_users)
    return DeleteEmployeeResponse(
        success=True,
        deleted_account_id=account_id,
        deleted_users=deleted_users,
    )


@router.get("/logs/analytics", response_model=LogsAnalyticsResponse)
def logs_analytics(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> LogsAnalyticsResponse:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rec_logs = db.execute(
        select(models.RecognitionLog).where(models.RecognitionLog.created_at >= since)
    ).scalars().all()
    total_rec = len(rec_logs)
    accepted = sum(1 for r in rec_logs if r.matched)
    rejected = total_rec - accepted

    login_count = db.execute(
        select(func.count(models.ActivityLog.id)).where(
            models.ActivityLog.event_type == "login",
            models.ActivityLog.created_at >= since,
        )
    ).scalar_one()

    active = db.execute(
        select(func.count(models.AuthSession.id)).where(models.AuthSession.is_active.is_(True))
    ).scalar_one()

    by_day: dict[str, int] = {}
    for r in rec_logs:
        key = r.created_at.strftime("%Y-%m-%d")
        by_day[key] = by_day.get(key, 0) + 1
    recognition_by_day = [
        TimeSeriesPoint(label=k, count=v)
        for k, v in sorted(by_day.items())
    ]

    act_rows = db.execute(
        select(models.ActivityLog.event_type, func.count())
        .where(models.ActivityLog.created_at >= since)
        .group_by(models.ActivityLog.event_type)
    ).all()
    activity_by_type = [
        TimeSeriesPoint(label=str(et), count=int(n)) for et, n in act_rows
    ]

    emp_rows = db.execute(
        select(models.Account.full_name, func.count(models.ActivityLog.id))
        .join(models.ActivityLog, models.ActivityLog.account_id == models.Account.id)
        .where(models.ActivityLog.created_at >= since)
        .group_by(models.Account.full_name)
        .order_by(func.count(models.ActivityLog.id).desc())
        .limit(10)
    ).all()
    events_by_employee = [
        TimeSeriesPoint(label=str(name), count=int(n)) for name, n in emp_rows
    ]

    return LogsAnalyticsResponse(
        total_recognition=total_rec,
        accepted=accepted,
        rejected=rejected,
        total_logins=int(login_count),
        active_sessions=int(active),
        recognition_by_day=recognition_by_day,
        activity_by_type=activity_by_type,
        events_by_employee=events_by_employee,
    )


class InviteCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=256)
    email: str = Field(min_length=3, max_length=256)


class InviteEntry(BaseModel):
    id: int
    token: str
    email: str
    full_name: str
    status: str
    expires_at: datetime
    created_at: datetime
    signup_url: str


class InvitesListResponse(BaseModel):
    count: int
    invites: list[InviteEntry]


class InviteCreateResponse(BaseModel):
    success: bool
    invite: InviteEntry


class AttendanceDayAdmin(BaseModel):
    work_date: str
    status: str
    first_login_at: Optional[datetime] = None
    last_logout_at: Optional[datetime] = None
    total_seconds: int
    session_count: int


@router.get("/invites", response_model=InvitesListResponse)
def list_invites(
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> InvitesListResponse:
    rows = db.execute(
        select(models.EmployeeInvite).order_by(models.EmployeeInvite.created_at.desc())
    ).scalars().all()
    items = [
        InviteEntry(
            id=r.id,
            token=r.token,
            email=r.email,
            full_name=r.full_name,
            status=r.status,
            expires_at=r.expires_at,
            created_at=r.created_at,
            signup_url=f"/employee/signup?invite={r.token}",
        )
        for r in rows
    ]
    return InvitesListResponse(count=len(items), invites=items)


@router.post("/invites", response_model=InviteCreateResponse)
def create_invite_route(
    body: InviteCreateRequest,
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> InviteCreateResponse:
    try:
        invite = create_invite(
            db,
            email=body.email,
            full_name=body.full_name,
            invited_by_account_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    entry = InviteEntry(
        id=invite.id,
        token=invite.token,
        email=invite.email,
        full_name=invite.full_name,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        signup_url=f"/employee/signup?invite={invite.token}",
    )
    return InviteCreateResponse(success=True, invite=entry)


@router.post("/invites/{invite_id}/revoke")
def revoke_invite_route(
    invite_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> dict:
    if not revoke_invite(db, invite_id):
        raise HTTPException(status_code=404, detail="Invite not found or not pending")
    return {"success": True}


@router.get("/employees/{account_id}/attendance", response_model=list[AttendanceDayAdmin])
def employee_attendance_admin(
    account_id: int,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> list[AttendanceDayAdmin]:
    acc = db.get(models.Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Employee not found")
    rows = db.execute(
        select(models.AttendanceRecord)
        .where(
            models.AttendanceRecord.account_id == account_id,
            models.AttendanceRecord.work_date.startswith(month),
        )
        .order_by(models.AttendanceRecord.work_date.desc())
    ).scalars().all()
    return [
        AttendanceDayAdmin(
            work_date=r.work_date,
            status=r.status,
            first_login_at=r.first_login_at,
            last_logout_at=r.last_logout_at,
            total_seconds=r.total_seconds or 0,
            session_count=r.session_count or 0,
        )
        for r in rows
    ]


class CompanySettingsResponse(BaseModel):
    work_day_start: str
    grace_minutes: int
    timezone: str
    require_palm_logout: bool
    exclude_weekends: bool
    half_day_hours: float
    notify_absent: bool
    notify_weekly_summary: bool
    admin_notify_email: Optional[str] = None
    smtp_configured: bool = False


class CompanySettingsUpdateRequest(BaseModel):
    work_day_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    grace_minutes: Optional[int] = Field(default=None, ge=0, le=240)
    timezone: Optional[str] = Field(default=None, min_length=2, max_length=64)
    require_palm_logout: Optional[bool] = None
    exclude_weekends: Optional[bool] = None
    half_day_hours: Optional[float] = Field(default=None, ge=0.5, le=12)
    notify_absent: Optional[bool] = None
    notify_weekly_summary: Optional[bool] = None
    admin_notify_email: Optional[str] = Field(default=None, max_length=256)


class CloseDayRequest(BaseModel):
    work_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class CloseDayResponse(BaseModel):
    success: bool
    work_date: str
    marked_absent: int
    half_days: int = 0
    skipped: bool = False
    reason: Optional[str] = None


class AttendanceOverrideRequest(BaseModel):
    work_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: Literal["present", "absent", "late", "leave", "half_day"]
    note: Optional[str] = Field(default=None, max_length=512)


class HolidayEntry(BaseModel):
    id: int
    holiday_date: str
    name: str
    created_at: datetime


class HolidaysListResponse(BaseModel):
    count: int
    holidays: list[HolidayEntry]


class HolidayCreateRequest(BaseModel):
    holiday_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    name: str = Field(min_length=1, max_length=128)


class WeeklySummaryResponse(BaseModel):
    sent: bool
    to: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    reason: Optional[str] = None


class TestEmailRequest(BaseModel):
    to: Optional[str] = Field(default=None, max_length=256)


class TestEmailResponse(BaseModel):
    sent: bool
    to: Optional[str] = None
    reason: Optional[str] = None


class NotificationSettingsResponse(BaseModel):
    admin_notify_email: Optional[str] = None
    notify_absent: bool
    notify_weekly_summary: bool
    smtp_configured: bool
    smtp_password_set: bool = False
    smtp_host: Optional[str] = None
    smtp_from: Optional[str] = None
    resolved_recipient: Optional[str] = None


class AttendanceReportRow(BaseModel):
    account_id: int
    full_name: str
    email: str
    work_date: str
    status: str
    first_login_at: Optional[datetime] = None
    last_logout_at: Optional[datetime] = None
    total_seconds: int
    session_count: int
    marked_by: str
    note: Optional[str] = None


class AttendanceReportResponse(BaseModel):
    count: int
    date_from: str
    date_to: str
    rows: list[AttendanceReportRow]


def _settings_response(s: models.CompanySettings) -> CompanySettingsResponse:
    return CompanySettingsResponse(
        work_day_start=s.work_day_start,
        grace_minutes=s.grace_minutes,
        timezone=s.timezone,
        require_palm_logout=s.require_palm_logout,
        exclude_weekends=s.exclude_weekends,
        half_day_hours=s.half_day_hours,
        notify_absent=s.notify_absent,
        notify_weekly_summary=s.notify_weekly_summary,
        admin_notify_email=s.admin_notify_email,
        smtp_configured=smtp_configured(),
    )


@router.get("/settings/attendance", response_model=CompanySettingsResponse)
def get_attendance_settings(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> CompanySettingsResponse:
    return _settings_response(get_settings(db))


@router.patch("/settings/attendance", response_model=CompanySettingsResponse)
def patch_attendance_settings(
    body: CompanySettingsUpdateRequest,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> CompanySettingsResponse:
    if body.timezone is not None:
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(body.timezone)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid timezone") from exc
    s = update_settings(
        db,
        work_day_start=body.work_day_start,
        grace_minutes=body.grace_minutes,
        timezone=body.timezone,
        require_palm_logout=body.require_palm_logout,
        exclude_weekends=body.exclude_weekends,
        half_day_hours=body.half_day_hours,
        notify_absent=body.notify_absent,
        notify_weekly_summary=body.notify_weekly_summary,
        admin_notify_email=body.admin_notify_email,
    )
    return _settings_response(s)


@router.post("/attendance/close-day", response_model=CloseDayResponse)
def close_attendance_day(
    body: CloseDayRequest,
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> CloseDayResponse:
    result = close_day_absences(
        db,
        work_date=body.work_date,
        admin_account_id=admin.id,
    )
    return CloseDayResponse(
        success=True,
        work_date=str(result["work_date"]),
        marked_absent=int(result["marked_absent"]),
        half_days=int(result.get("half_days", 0)),
        skipped=bool(result.get("skipped", False)),
        reason=str(result.get("reason") or "") or None,
    )


@router.post("/employees/{account_id}/attendance/override", response_model=AttendanceDayAdmin)
def override_employee_attendance(
    account_id: int,
    body: AttendanceOverrideRequest,
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> AttendanceDayAdmin:
    try:
        rec = override_attendance(
            db,
            account_id=account_id,
            work_date=body.work_date,
            status=body.status,
            note=body.note,
            admin_account_id=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AttendanceDayAdmin(
        work_date=rec.work_date,
        status=rec.status,
        first_login_at=rec.first_login_at,
        last_logout_at=rec.last_logout_at,
        total_seconds=rec.total_seconds or 0,
        session_count=rec.session_count or 0,
    )


@router.get("/attendance/report", response_model=AttendanceReportResponse)
def attendance_report(
    date_from: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> AttendanceReportResponse:
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")
    raw = list_attendance_report(db, date_from=date_from, date_to=date_to)
    rows = [AttendanceReportRow(**r) for r in raw]
    return AttendanceReportResponse(
        count=len(rows),
        date_from=date_from,
        date_to=date_to,
        rows=rows,
    )


@router.get("/attendance/report.csv")
def attendance_report_csv(
    date_from: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> StreamingResponse:
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be <= date_to")
    raw = list_attendance_report(db, date_from=date_from, date_to=date_to)
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "full_name",
        "email",
        "work_date",
        "status",
        "first_login_at",
        "last_logout_at",
        "total_hours",
        "session_count",
        "marked_by",
        "note",
    ])
    for r in raw:
        hours = round((r["total_seconds"] or 0) / 3600, 2)
        writer.writerow([
            r["full_name"],
            r["email"],
            r["work_date"],
            r["status"],
            r["first_login_at"].isoformat() if r["first_login_at"] else "",
            r["last_logout_at"].isoformat() if r["last_logout_at"] else "",
            hours,
            r["session_count"],
            r["marked_by"],
            r["note"] or "",
        ])
    buf.seek(0)
    filename = f"attendance_{date_from}_{date_to}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/holidays", response_model=HolidaysListResponse)
def list_holidays_route(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> HolidaysListResponse:
    rows = list_holidays(db)
    items = [
        HolidayEntry(id=r.id, holiday_date=r.holiday_date, name=r.name, created_at=r.created_at)
        for r in rows
    ]
    return HolidaysListResponse(count=len(items), holidays=items)


@router.post("/holidays", response_model=HolidayEntry)
def create_holiday_route(
    body: HolidayCreateRequest,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> HolidayEntry:
    row = add_holiday(db, holiday_date=body.holiday_date, name=body.name)
    return HolidayEntry(
        id=row.id,
        holiday_date=row.holiday_date,
        name=row.name,
        created_at=row.created_at,
    )


@router.delete("/holidays/{holiday_id}")
def delete_holiday_route(
    holiday_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> dict:
    if not delete_holiday(db, holiday_id):
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"success": True}


@router.get("/notifications/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> NotificationSettingsResponse:
    admin_email = get_primary_admin_email(db)
    if admin_email:
        update_settings(db, admin_notify_email=admin_email)
    s = get_settings(db)
    return NotificationSettingsResponse(
        admin_notify_email=admin_email,
        notify_absent=s.notify_absent,
        notify_weekly_summary=s.notify_weekly_summary,
        smtp_configured=smtp_configured(),
        smtp_password_set=bool(SMTP_PASSWORD),
        smtp_host=SMTP_HOST or None,
        smtp_from=SMTP_FROM if SMTP_HOST else None,
        resolved_recipient=admin_email,
    )


@router.post("/notifications/test-email", response_model=TestEmailResponse)
def test_notification_email(
    body: TestEmailRequest,
    db: Session = Depends(get_db),
    admin: models.Account = Depends(require_admin),
) -> TestEmailResponse:
    del body
    to = resolve_admin_notify_email(db, fallback_admin=admin)
    if not to:
        return TestEmailResponse(sent=False, reason="no_recipient")
    result = send_test_email(to=to)
    return TestEmailResponse(**result)


@router.post("/attendance/weekly-summary", response_model=WeeklySummaryResponse)
def send_weekly_summary_route(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> WeeklySummaryResponse:
    result = send_weekly_summary(db)
    return WeeklySummaryResponse(**result)


class CustomerSummary(BaseModel):
    account_id: int
    full_name: str
    email: str
    dataset_id: str
    registered_at: datetime
    left_enrolled: bool
    right_enrolled: bool
    activity_count: int
    last_activity_at: Optional[datetime] = None


class CustomersListResponse(BaseModel):
    count: int
    customers: list[CustomerSummary]


class CustomerDetailResponse(BaseModel):
    account_id: int
    full_name: str
    email: str
    dataset_id: str
    dataset_name: str
    role: str
    registered_at: datetime
    left_enrolled: bool
    right_enrolled: bool
    activities: list[ActivityEntry]


@router.get("/customers", response_model=CustomersListResponse)
def list_customers(
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> CustomersListResponse:
    accounts = db.execute(
        select(models.Account)
        .where(models.Account.role == "customer")
        .order_by(models.Account.created_at.desc())
    ).scalars().all()
    items: list[CustomerSummary] = []
    for acc in accounts:
        act_count = db.execute(
            select(func.count())
            .select_from(models.ActivityLog)
            .where(models.ActivityLog.account_id == acc.id)
        ).scalar_one()
        last_act = db.execute(
            select(models.ActivityLog)
            .where(models.ActivityLog.account_id == acc.id)
            .order_by(models.ActivityLog.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        items.append(
            CustomerSummary(
                account_id=acc.id,
                full_name=acc.full_name,
                email=acc.email,
                dataset_id=acc.dataset_id,
                registered_at=acc.created_at,
                left_enrolled=acc.left_template is not None,
                right_enrolled=acc.right_template is not None,
                activity_count=int(act_count or 0),
                last_activity_at=last_act.created_at if last_act else None,
            )
        )
    return CustomersListResponse(count=len(items), customers=items)


@router.get("/customers/{account_id}", response_model=CustomerDetailResponse)
def customer_detail(
    account_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> CustomerDetailResponse:
    acc = db.get(models.Account, account_id)
    if acc is None or acc.role != "customer":
        raise HTTPException(status_code=404, detail="Customer not found")
    activities = db.execute(
        select(models.ActivityLog)
        .where(models.ActivityLog.account_id == acc.id)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(100)
    ).scalars().all()
    return CustomerDetailResponse(
        account_id=acc.id,
        full_name=acc.full_name,
        email=acc.email,
        dataset_id=acc.dataset_id,
        dataset_name=acc.dataset_name,
        role=acc.role,
        registered_at=acc.created_at,
        left_enrolled=acc.left_template is not None,
        right_enrolled=acc.right_template is not None,
        activities=[
            ActivityEntry(
                id=a.id,
                event_type=a.event_type,
                detail=a.detail,
                created_at=a.created_at,
            )
            for a in activities
        ],
    )


@router.delete("/customers/{account_id}")
def delete_customer(
    account_id: int,
    db: Session = Depends(get_db),
    _: models.Account = Depends(require_admin),
) -> dict:
    acc = db.get(models.Account, account_id)
    if acc is None or acc.role != "customer":
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(acc)
    db.commit()
    return {"success": True, "deleted_account_id": account_id}

