"""HR employee invite tokens."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import models


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_invite(
    db: Session,
    *,
    email: str,
    full_name: str,
    invited_by_account_id: int,
    expires_days: int = 7,
) -> models.EmployeeInvite:
    email_l = email.lower().strip()
    existing = db.execute(
        select(models.EmployeeInvite).where(
            models.EmployeeInvite.email == email_l,
            models.EmployeeInvite.status == "pending",
        )
    ).scalar_one_or_none()
    if existing and existing.expires_at > _utcnow():
        raise ValueError("A pending invite already exists for this email")

    if db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none():
        raise ValueError("An account with this email already exists")

    token = secrets.token_urlsafe(32)
    invite = models.EmployeeInvite(
        token=token,
        email=email_l,
        full_name=full_name.strip(),
        status="pending",
        invited_by_account_id=invited_by_account_id,
        expires_at=_utcnow() + timedelta(days=expires_days),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def get_valid_invite(db: Session, token: str) -> Optional[models.EmployeeInvite]:
    invite = db.execute(
        select(models.EmployeeInvite).where(models.EmployeeInvite.token == token)
    ).scalar_one_or_none()
    if invite is None or invite.status != "pending":
        return None
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < _utcnow():
        return None
    return invite


def mark_invite_used(
    db: Session,
    invite: models.EmployeeInvite,
    account_id: int,
) -> None:
    invite.status = "used"
    invite.account_id = account_id
    invite.used_at = _utcnow()
    db.flush()


def revoke_invite(db: Session, invite_id: int) -> bool:
    invite = db.get(models.EmployeeInvite, invite_id)
    if invite is None or invite.status != "pending":
        return False
    invite.status = "revoked"
    db.commit()
    return True
