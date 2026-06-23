"""Employee session and activity logging."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import models


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def start_session(
    db: Session,
    *,
    account_id: int,
    login_method: str,
) -> models.AuthSession:
    account = db.get(models.Account, account_id)
    open_rows = db.execute(
        select(models.AuthSession).where(
            models.AuthSession.account_id == account_id,
            models.AuthSession.is_active.is_(True),
        )
    ).scalars().all()
    for open_sess in open_rows:
        _close_session(open_sess, db=db, account=account, logout_method="auto_relogin")

    sess = models.AuthSession(
        account_id=account_id,
        login_method=login_method,
        login_at=_utcnow(),
        is_active=True,
    )
    db.add(sess)
    db.flush()
    log_activity(
        db,
        account_id=account_id,
        session_id=sess.id,
        event_type="login",
        detail=f"method={login_method}",
    )
    if account and account.role == "employee":
        from backend.auth.attendance import record_login_attendance

        record_login_attendance(db, account=account, session=sess)
    db.commit()
    db.refresh(sess)
    return sess


def _close_session(
    sess: models.AuthSession,
    *,
    db: Optional[Session] = None,
    account: Optional[models.Account] = None,
    logout_method: str = "email",
) -> None:
    now = _utcnow()
    sess.logout_at = now
    sess.is_active = False
    if sess.login_at:
        login_at = sess.login_at
        if login_at.tzinfo is None:
            login_at = login_at.replace(tzinfo=timezone.utc)
        sess.duration_seconds = max(0, int((now - login_at).total_seconds()))
    if db is not None and account is not None and account.role == "employee":
        from backend.auth.attendance import record_logout_attendance

        record_logout_attendance(db, account=account, session=sess, logout_method=logout_method)


def end_session(
    db: Session,
    *,
    account_id: int,
    session_id: Optional[int] = None,
    logout_method: str = "email",
) -> Optional[models.AuthSession]:
    account = db.get(models.Account, account_id)
    stmt = select(models.AuthSession).where(
        models.AuthSession.account_id == account_id,
        models.AuthSession.is_active.is_(True),
    )
    if session_id is not None:
        stmt = stmt.where(models.AuthSession.id == session_id)
    sess = db.execute(stmt.order_by(models.AuthSession.login_at.desc())).scalars().first()
    if not sess:
        return None
    _close_session(sess, db=db, account=account, logout_method=logout_method)
    log_activity(
        db,
        account_id=account_id,
        session_id=sess.id,
        event_type="logout",
        detail=f"duration_seconds={sess.duration_seconds};method={logout_method}",
    )
    db.commit()
    db.refresh(sess)
    return sess


def log_activity(
    db: Session,
    *,
    account_id: Optional[int],
    event_type: str,
    detail: Optional[str] = None,
    session_id: Optional[int] = None,
    commit: bool = False,
) -> models.ActivityLog:
    row = models.ActivityLog(
        account_id=account_id,
        session_id=session_id,
        event_type=event_type,
        detail=detail,
        created_at=_utcnow(),
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row
