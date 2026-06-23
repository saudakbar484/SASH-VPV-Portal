#!/usr/bin/env python3
"""Ensure Saud Akbar account has admin role and refresh palm login templates."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text

from backend.auth.template_cache import refresh_account_templates
from backend.db.base import SessionLocal
from backend.db import models

ADMIN_EMAIL = "saudakbar65367@gmail.com"


def main() -> None:
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE accounts SET role = 'admin', email_verified = 1 WHERE email = :email"),
            {"email": ADMIN_EMAIL},
        )
        db.commit()
        acc = db.execute(
            select(models.Account).where(models.Account.email == ADMIN_EMAIL)
        ).scalar_one_or_none()
        if not acc:
            print(f"ERROR: No account found for {ADMIN_EMAIL}")
            sys.exit(1)
        acc.role = "admin"
        acc.email_verified = True
        db.commit()
        db.refresh(acc)
        n = refresh_account_templates(db)
        print(f"OK: {acc.full_name} ({acc.email}) role={acc.role} templates={n}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
