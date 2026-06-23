"""Daily attendance tracking for employee login/logout."""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.activity import log_activity
from backend.db import models

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_settings(db: Session) -> models.CompanySettings:
    row = db.get(models.CompanySettings, 1)
    if row is None:
        row = models.CompanySettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def work_date_str(db: Session, when: Optional[datetime] = None) -> str:
    settings = get_settings(db)
    tz = ZoneInfo(settings.timezone)
    dt = when or _utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date().isoformat()


def _parse_work_start(settings: models.CompanySettings, work_date: str) -> datetime:
    tz = ZoneInfo(settings.timezone)
    hour, minute = map(int, settings.work_day_start.split(":"))
    local_date = datetime.fromisoformat(work_date).date()
    local_dt = datetime.combine(local_date, time(hour, minute), tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def _status_for_login(db: Session, login_at: datetime) -> str:
    settings = get_settings(db)
    work_date = work_date_str(db, login_at)
    start = _parse_work_start(settings, work_date)
    grace_end = start.timestamp() + settings.grace_minutes * 60
    if login_at.timestamp() > grace_end:
        return "late"
    return "present"


def get_or_create_today_record(
    db: Session, account_id: int, *, work_date: Optional[str] = None
) -> models.AttendanceRecord:
    wd = work_date or work_date_str(db)
    row = db.execute(
        select(models.AttendanceRecord).where(
            models.AttendanceRecord.account_id == account_id,
            models.AttendanceRecord.work_date == wd,
        )
    ).scalar_one_or_none()
    if row:
        return row
    row = models.AttendanceRecord(
        account_id=account_id,
        work_date=wd,
        status="absent",
        marked_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _half_day_threshold_seconds(settings: models.CompanySettings) -> int:
    return int(max(settings.half_day_hours, 0.5) * 3600)


def is_work_day(db: Session, work_date: str) -> tuple[bool, str]:
    settings = get_settings(db)
    d = date.fromisoformat(work_date)
    if settings.exclude_weekends and d.weekday() >= 5:
        return False, "weekend"
    holiday = db.execute(
        select(models.CompanyHoliday).where(models.CompanyHoliday.holiday_date == work_date)
    ).scalar_one_or_none()
    if holiday:
        return False, f"holiday:{holiday.name}"
    return True, ""


def apply_half_day_if_needed(db: Session, record: models.AttendanceRecord) -> None:
    if record.first_login_at is None:
        return
    if record.status in ("absent", "leave", "half_day"):
        return
    settings = get_settings(db)
    threshold = _half_day_threshold_seconds(settings)
    if (record.total_seconds or 0) < threshold:
        record.status = "half_day"
        record.updated_at = _utcnow()


def record_login_attendance(
    db: Session,
    *,
    account: models.Account,
    session: models.AuthSession,
    login_at: Optional[datetime] = None,
) -> Optional[models.AttendanceRecord]:
    if account.role != "employee":
        return None

    now = login_at or _utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    record = get_or_create_today_record(db, account.id, work_date=work_date_str(db, now))
    is_first_login_today = record.first_login_at is None

    if is_first_login_today:
        record.first_login_at = now
        record.status = _status_for_login(db, now)
        record.marked_by = "system"
        event = "attendance_late" if record.status == "late" else "attendance_present"
        log_activity(
            db,
            account_id=account.id,
            session_id=session.id,
            event_type=event,
            detail=f"work_date={record.work_date}",
        )
    else:
        record.session_count = max(record.session_count, 0)

    record.session_count += 1
    record.updated_at = _utcnow()
    session.attendance_record_id = record.id
    db.flush()
    return record


def record_logout_attendance(
    db: Session,
    *,
    account: models.Account,
    session: models.AuthSession,
    logout_method: str = "email",
) -> None:
    if account.role != "employee":
        return

    duration = session.duration_seconds or 0
    now = session.logout_at or _utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    record = None
    if session.attendance_record_id:
        record = db.get(models.AttendanceRecord, session.attendance_record_id)
    if record is None:
        record = get_or_create_today_record(db, account.id, work_date=work_date_str(db, now))

    record.last_logout_at = now
    record.total_seconds = (record.total_seconds or 0) + duration
    apply_half_day_if_needed(db, record)
    record.updated_at = _utcnow()
    session.logout_method = logout_method

    event = "logout_palm_verified" if logout_method == "palm" else "logout"
    if logout_method == "email_fallback":
        event = "logout_email_fallback"
    log_activity(
        db,
        account_id=account.id,
        session_id=session.id,
        event_type=event,
        detail=f"duration_seconds={duration}",
    )
    db.flush()


def close_day_absences(
    db: Session,
    *,
    work_date: Optional[str] = None,
    admin_account_id: Optional[int] = None,
) -> dict[str, int | str | bool]:
    """Mark employees absent for a work day if they never checked in."""
    from backend.auth.notifications import notify_absent

    wd = work_date or work_date_str(db)
    ok, reason = is_work_day(db, wd)
    if not ok:
        logger.info("Skipping close_day for %s (%s)", wd, reason)
        return {"work_date": wd, "marked_absent": 0, "skipped": True, "reason": reason}

    employees = db.execute(
        select(models.Account).where(models.Account.role == "employee")
    ).scalars().all()
    marked = 0
    half_days = 0
    marked_by = "admin" if admin_account_id else "system"
    settings = get_settings(db)

    for acc in employees:
        rec = db.execute(
            select(models.AttendanceRecord).where(
                models.AttendanceRecord.account_id == acc.id,
                models.AttendanceRecord.work_date == wd,
            )
        ).scalar_one_or_none()

        if rec is not None and rec.first_login_at is not None:
            before = rec.status
            apply_half_day_if_needed(db, rec)
            if rec.status == "half_day" and before != "half_day":
                half_days += 1
            continue

        if rec is None:
            rec = models.AttendanceRecord(
                account_id=acc.id,
                work_date=wd,
                status="absent",
                marked_by=marked_by,
            )
            db.add(rec)
        elif rec.status not in ("present", "late", "leave", "half_day"):
            rec.status = "absent"
            rec.marked_by = marked_by
            rec.updated_at = _utcnow()
        else:
            continue

        log_activity(
            db,
            account_id=acc.id,
            event_type="attendance_absent",
            detail=f"work_date={wd};marked_by={marked_by}",
        )
        if settings.notify_absent:
            notify_absent(db, account=acc, work_date=wd)
        marked += 1

    db.commit()
    logger.info(
        "Closed attendance day %s: %d marked absent, %d half-days",
        wd,
        marked,
        half_days,
    )
    return {
        "work_date": wd,
        "marked_absent": marked,
        "half_days": half_days,
        "skipped": False,
        "reason": "",
    }


def close_yesterday_if_needed(db: Session) -> None:
    """On startup: ensure yesterday has absent rows for no-shows."""
    settings = get_settings(db)
    tz = ZoneInfo(settings.timezone)
    yesterday = (datetime.now(tz).date() - timedelta(days=1)).isoformat()
    close_day_absences(db, work_date=yesterday)
    if settings.notify_weekly_summary and datetime.now(tz).weekday() == 0:
        from backend.auth.notifications import send_weekly_summary

        send_weekly_summary(db)


def override_attendance(
    db: Session,
    *,
    account_id: int,
    work_date: str,
    status: str,
    note: Optional[str],
    admin_account_id: int,
) -> models.AttendanceRecord:
    allowed = {"present", "absent", "late", "leave", "half_day"}
    if status not in allowed:
        raise ValueError(f"status must be one of {allowed}")

    acc = db.get(models.Account, account_id)
    if acc is None or acc.role != "employee":
        raise ValueError("Employee not found")

    rec = db.execute(
        select(models.AttendanceRecord).where(
            models.AttendanceRecord.account_id == account_id,
            models.AttendanceRecord.work_date == work_date,
        )
    ).scalar_one_or_none()
    if rec is None:
        rec = models.AttendanceRecord(
            account_id=account_id,
            work_date=work_date,
            status=status,
            marked_by="admin",
            note=note,
        )
        db.add(rec)
    else:
        rec.status = status
        rec.marked_by = "admin"
        rec.note = note
        rec.updated_at = _utcnow()
        if status in ("present", "late") and rec.first_login_at is None:
            rec.first_login_at = _utcnow()
    log_activity(
        db,
        account_id=account_id,
        event_type="attendance_manual",
        detail=f"work_date={work_date};status={status};note={note or ''};admin_id={admin_account_id}",
    )
    db.commit()
    db.refresh(rec)
    return rec


def list_attendance_report(
    db: Session,
    *,
    date_from: str,
    date_to: str,
) -> list[dict]:
    rows = db.execute(
        select(models.AttendanceRecord, models.Account)
        .join(models.Account, models.Account.id == models.AttendanceRecord.account_id)
        .where(
            models.Account.role == "employee",
            models.AttendanceRecord.work_date >= date_from,
            models.AttendanceRecord.work_date <= date_to,
        )
        .order_by(models.AttendanceRecord.work_date.desc(), models.Account.full_name)
    ).all()
    return [
        {
            "account_id": acc.id,
            "full_name": acc.full_name,
            "email": acc.email,
            "work_date": rec.work_date,
            "status": rec.status,
            "first_login_at": rec.first_login_at,
            "last_logout_at": rec.last_logout_at,
            "total_seconds": rec.total_seconds or 0,
            "session_count": rec.session_count or 0,
            "marked_by": rec.marked_by,
            "note": rec.note,
        }
        for rec, acc in rows
    ]


def update_settings(
    db: Session,
    *,
    work_day_start: Optional[str] = None,
    grace_minutes: Optional[int] = None,
    timezone: Optional[str] = None,
    require_palm_logout: Optional[bool] = None,
    exclude_weekends: Optional[bool] = None,
    half_day_hours: Optional[float] = None,
    notify_absent: Optional[bool] = None,
    notify_weekly_summary: Optional[bool] = None,
    admin_notify_email: Optional[str] = None,
) -> models.CompanySettings:
    settings = get_settings(db)
    if work_day_start is not None:
        settings.work_day_start = work_day_start
    if grace_minutes is not None:
        settings.grace_minutes = grace_minutes
    if timezone is not None:
        settings.timezone = timezone
    if require_palm_logout is not None:
        settings.require_palm_logout = require_palm_logout
    if exclude_weekends is not None:
        settings.exclude_weekends = exclude_weekends
    if half_day_hours is not None:
        settings.half_day_hours = half_day_hours
    if notify_absent is not None:
        settings.notify_absent = notify_absent
    if notify_weekly_summary is not None:
        settings.notify_weekly_summary = notify_weekly_summary
    if admin_notify_email is not None:
        settings.admin_notify_email = admin_notify_email or None
    db.commit()
    db.refresh(settings)
    return settings


def list_holidays(db: Session) -> list[models.CompanyHoliday]:
    return list(
        db.execute(
            select(models.CompanyHoliday).order_by(models.CompanyHoliday.holiday_date.desc())
        ).scalars().all()
    )


def add_holiday(db: Session, *, holiday_date: str, name: str) -> models.CompanyHoliday:
    existing = db.execute(
        select(models.CompanyHoliday).where(models.CompanyHoliday.holiday_date == holiday_date)
    ).scalar_one_or_none()
    if existing:
        existing.name = name
        db.commit()
        db.refresh(existing)
        return existing
    row = models.CompanyHoliday(holiday_date=holiday_date, name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_holiday(db: Session, holiday_id: int) -> bool:
    row = db.get(models.CompanyHoliday, holiday_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
