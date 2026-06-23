"""Optional auth dependency for protected routes."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.jwt_tokens import decode_access_token
from backend.db import models
from backend.deps import get_db

_bearer = HTTPBearer(auto_error=False)


def get_current_account(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.Account:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(creds.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    account = db.get(models.Account, int(payload["sub"]))
    if account is None:
        raise HTTPException(status_code=401, detail="Account not found")
    return account


def get_optional_account(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[models.Account]:
    if creds is None or not creds.credentials:
        return None
    payload = decode_access_token(creds.credentials)
    if payload is None:
        return None
    return db.get(models.Account, int(payload["sub"]))


def require_employee(account: models.Account = Depends(get_current_account)) -> models.Account:
    if account.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required")
    return account


def require_customer(account: models.Account = Depends(get_current_account)) -> models.Account:
    if account.role != "customer":
        raise HTTPException(status_code=403, detail="Customer access required")
    return account
