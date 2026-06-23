"""Email verification codes for signup (all roles)."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.auth.notifications import send_email_detailed
from backend.db import models

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 15
CODE_LENGTH = 6


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def _role_label(role: str) -> str:
    if role == "admin":
        return "admin"
    if role == "customer":
        return "member"
    return "employee"


def issue_verification_code(db: Session, account: models.Account) -> dict:
    """Create a new code, invalidate prior codes, and email the user."""
    code = _generate_code()
    expires_at = _utcnow() + timedelta(minutes=CODE_TTL_MINUTES)

    db.execute(delete(models.EmailVerificationCode).where(models.EmailVerificationCode.account_id == account.id))
    db.add(
        models.EmailVerificationCode(
            account_id=account.id,
            code=code,
            expires_at=expires_at,
        )
    )
    db.commit()

    display_name = account.username or account.full_name
    portal = _role_label(account.role)
    body = (
        f"Hi {display_name},\n\n"
        f"Your Palm Vein {portal} account verification code is: {code}\n\n"
        f"This code expires in {CODE_TTL_MINUTES} minutes.\n"
        f"If you did not create an account, you can ignore this email.\n"
    )
    result = send_email_detailed(
        to=account.email,
        subject="Verify your Palm Vein account",
        body=body,
    )
    if not result.get("sent"):
        logger.warning("Verification email not sent to %s: %s", account.email, result.get("reason"))
    return {"sent": bool(result.get("sent")), "reason": result.get("reason"), "expires_at": expires_at}


def verify_email_code(db: Session, *, email: str, code: str) -> models.Account:
    email_l = email.lower().strip()
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    if account is None:
        raise ValueError("No account found for this email")

    row = db.execute(
        select(models.EmailVerificationCode)
        .where(models.EmailVerificationCode.account_id == account.id)
        .order_by(models.EmailVerificationCode.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if row is None:
        raise ValueError("No verification code found — request a new one")
    expires = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expires < _utcnow():
        raise ValueError("Verification code expired — request a new one")
    if row.code.strip() != code.strip():
        raise ValueError("Invalid verification code")

    account.email_verified = True
    db.execute(delete(models.EmailVerificationCode).where(models.EmailVerificationCode.account_id == account.id))
    db.commit()
    db.refresh(account)
    return account
