"""Optional email notifications for attendance events."""
from __future__ import annotations

import logging
import smtplib
from datetime import timedelta
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.attendance import get_settings, work_date_str
from backend.db import models
from backend.settings import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM and SMTP_PASSWORD)


def send_email_detailed(*, to: str, subject: str, body: str) -> dict:
    if not smtp_configured():
        logger.info("Email (not sent — SMTP not configured): to=%s subject=%s", to, subject)
        return {"sent": False, "reason": "smtp_not_configured"}
    if not to:
        return {"sent": False, "reason": "no_recipient"}
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return {"sent": True}
    except smtplib.SMTPAuthenticationError as exc:
        logger.exception("SMTP authentication failed for user %s", SMTP_USER)
        err = str(exc.args[-1] if exc.args else exc).lower()
        if "unauthorized ip" in err or exc.smtp_code == 525:
            return {"sent": False, "reason": "smtp_ip_blocked"}
        return {"sent": False, "reason": "smtp_auth_failed"}
    except smtplib.SMTPException:
        logger.exception("SMTP error sending email to %s", to)
        return {"sent": False, "reason": "send_failed"}
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return {"sent": False, "reason": "send_failed"}


def send_email(*, to: str, subject: str, body: str) -> bool:
    return send_email_detailed(to=to, subject=subject, body=body)["sent"]


def notify_absent(db: Session, *, account: models.Account, work_date: str) -> None:
    settings = get_settings(db)
    if not settings.notify_absent:
        return
    send_email(
        to=account.email,
        subject=f"Attendance: marked absent for {work_date}",
        body=(
            f"Hi {account.full_name},\n\n"
            f"You were marked absent for {work_date} because no check-in was recorded.\n"
            f"If this is incorrect, contact HR.\n"
        ),
    )


def get_primary_admin_email(db: Session) -> Optional[str]:
    admin = db.execute(
        select(models.Account).where(models.Account.role == "admin").order_by(models.Account.id)
    ).scalar_one_or_none()
    if admin and admin.email:
        return admin.email.strip()
    return None


def resolve_admin_notify_email(
    db: Session,
    *,
    preferred: Optional[str] = None,
    fallback_admin: Optional[models.Account] = None,
) -> Optional[str]:
    """HR / weekly-summary emails always go to the primary administrator account."""
    del preferred, fallback_admin
    return get_primary_admin_email(db)


def send_test_email(*, to: str) -> dict:
    if not to.strip():
        return {"sent": False, "reason": "no_recipient"}
    if not smtp_configured():
        send_email(
            to=to,
            subject="PalmVein test notification",
            body=(
                "This is a test message from PalmVein Workplace.\n\n"
                "SMTP is not configured on the server — this email was logged only, not delivered.\n"
            ),
        )
        return {"sent": False, "to": to, "reason": "smtp_not_configured"}
    result = send_email_detailed(
        to=to,
        subject="PalmVein test notification",
        body=(
            "This is a test message from PalmVein Workplace.\n\n"
            "If you received this, SMTP delivery is working correctly.\n"
        ),
    )
    return {"sent": result["sent"], "to": to, "reason": result.get("reason")}


def send_weekly_summary(db: Session, *, admin_email: Optional[str] = None) -> dict:
    settings = get_settings(db)
    to = resolve_admin_notify_email(db, preferred=admin_email)
    if not to:
        return {"sent": False, "reason": "no_admin_email"}

    from zoneinfo import ZoneInfo

    tz = ZoneInfo(settings.timezone)
    end = work_date_str(db)
    start = (datetime_from_iso(end) - timedelta(days=6)).isoformat()

    rows = db.execute(
        select(
            models.Account.full_name,
            models.AttendanceRecord.status,
            func.count(),
        )
        .join(models.AttendanceRecord, models.AttendanceRecord.account_id == models.Account.id)
        .where(
            models.Account.role == "employee",
            models.AttendanceRecord.work_date >= start,
            models.AttendanceRecord.work_date <= end,
        )
        .group_by(models.Account.full_name, models.AttendanceRecord.status)
        .order_by(models.Account.full_name)
    ).all()

    lines = [f"Weekly attendance summary ({start} to {end})", ""]
    if not rows:
        lines.append("No attendance records in this period.")
    else:
        current = ""
        for name, status, count in rows:
            if name != current:
                if current:
                    lines.append("")
                lines.append(f"{name}:")
                current = name
            lines.append(f"  {status}: {count}")

    body = "\n".join(lines) + f"\n\nTimezone: {settings.timezone}\n"
    result = send_email_detailed(
        to=to,
        subject=f"PalmVein weekly attendance ({start} – {end})",
        body=body,
    )
    return {
        "sent": result["sent"],
        "to": to,
        "date_from": start,
        "date_to": end,
        "reason": result.get("reason"),
    }


def datetime_from_iso(value: str):
    from datetime import date

    return date.fromisoformat(value)
