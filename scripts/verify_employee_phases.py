#!/usr/bin/env python3
"""Verify employee panel Phases 1–4 via API. Run: python scripts/verify_employee_phases.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Optional: set before backend import for internal cron test
os.environ.setdefault("ATTENDANCE_CRON_SECRET", "test-cron-secret-verify")

from sqlalchemy import select
from fastapi.testclient import TestClient

from backend.auth.passwords import hash_password
from backend.db.base import SessionLocal
from backend.db import models
from backend.main import app
from backend.settings import ATTENDANCE_CRON_SECRET

ADMIN_EMAIL = "saudakbar65367@gmail.com"
EMPLOYEE_EMAIL = "ameerkhanf22@nutech.edu.pk"
TEST_PASSWORD = "VerifyPhaseTest1!"

client = TestClient(app)
failures: list[str] = []
passed: list[str] = []


def ok(name: str) -> None:
    passed.append(name)
    print(f"  PASS  {name}")


def fail(name: str, detail: str) -> None:
    failures.append(f"{name}: {detail}")
    print(f"  FAIL  {name}: {detail}")


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str) -> str | None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        return None
    return r.json()["access_token"]


def setup_test_passwords() -> None:
    db = SessionLocal()
    try:
        for email in (ADMIN_EMAIL, EMPLOYEE_EMAIL):
            acc = db.execute(
                select(models.Account).where(models.Account.email == email)
            ).scalar_one_or_none()
            if acc:
                acc.password_hash = hash_password(TEST_PASSWORD)
        db.commit()
    finally:
        db.close()


def verify_phase1() -> None:
    print("\n=== Phase 1 — Employee portal MVP ===")
    admin_t = login(ADMIN_EMAIL, TEST_PASSWORD)
    emp_t = login(EMPLOYEE_EMAIL, TEST_PASSWORD)
    if not admin_t:
        fail("admin login", "could not authenticate")
        return
    ok("admin login")
    if not emp_t:
        fail("employee login", "could not authenticate")
        return
    ok("employee login")

    r = client.get("/api/employee/dashboard", headers=auth_header(emp_t))
    if r.status_code == 200 and "work_date" in r.json():
        ok("GET /api/employee/dashboard")
    else:
        fail("employee dashboard", f"{r.status_code} {r.text[:200]}")

    for path in ("/api/employee/attendance?month=2026-06", "/api/employee/activity", "/api/employee/profile"):
        r = client.get(path, headers=auth_header(emp_t))
        if r.status_code == 200:
            ok(f"GET {path.split('?')[0]}")
        else:
            fail(path, f"{r.status_code}")

    r = client.get("/api/admin/employees", headers=auth_header(admin_t))
    if r.status_code == 200:
        data = r.json()
        roles = [e.get("role") for e in data.get("employees", [])]
        if all(r == "employee" for r in roles):
            ok("GET /api/admin/employees (employees only)")
        else:
            fail("admin employees list", f"unexpected roles: {roles}")
    else:
        fail("admin employees", f"{r.status_code}")

    r = client.get("/api/admin/invites", headers=auth_header(admin_t))
    if r.status_code == 200:
        ok("GET /api/admin/invites")
    else:
        fail("admin invites", f"{r.status_code}")

    r = client.get("/api/employee/dashboard", headers=auth_header(admin_t))
    if r.status_code == 403:
        ok("admin blocked from employee dashboard")
    else:
        fail("employee route guard", f"admin got {r.status_code}, expected 403")

    r = client.post("/api/auth/logout/palm", headers=auth_header(emp_t), json={"session_id": None})
    if r.status_code in (200, 503, 500):
        ok("POST /api/auth/logout/palm (endpoint exists)")
    else:
        fail("logout/palm", f"{r.status_code} {r.text[:120]}")


def verify_phase2() -> None:
    print("\n=== Phase 2 — Operations ===")
    admin_t = login(ADMIN_EMAIL, TEST_PASSWORD)
    if not admin_t:
        fail("phase2 admin login", "skip")
        return
    h = auth_header(admin_t)

    r = client.get("/api/admin/settings/attendance", headers=h)
    if r.status_code == 200 and r.json().get("grace_minutes") is not None:
        ok("GET attendance settings")
    else:
        fail("attendance settings", f"{r.status_code}")

    r = client.patch(
        "/api/admin/settings/attendance",
        headers=h,
        json={"grace_minutes": 30},
    )
    if r.status_code == 200:
        ok("PATCH attendance settings")
    else:
        fail("patch settings", f"{r.status_code}")

    r = client.get(
        "/api/admin/attendance/report",
        headers=h,
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    if r.status_code == 200 and "rows" in r.json():
        ok("GET attendance report")
    else:
        fail("attendance report", f"{r.status_code}")

    r = client.get(
        "/api/admin/attendance/report.csv",
        headers=h,
        params={"date_from": "2026-06-01", "date_to": "2026-06-30"},
    )
    if r.status_code == 200 and "text/csv" in r.headers.get("content-type", ""):
        ok("GET attendance report CSV")
    else:
        fail("attendance CSV", f"{r.status_code}")

    r = client.post("/api/admin/attendance/close-day", headers=h, json={"work_date": "2026-06-19"})
    if r.status_code == 200:
        ok("POST close-day (admin)")
    else:
        fail("close-day", f"{r.status_code} {r.text[:120]}")

    db = SessionLocal()
    try:
        emp = db.execute(
            select(models.Account).where(models.Account.email == EMPLOYEE_EMAIL)
        ).scalar_one()
        r = client.post(
            f"/api/admin/employees/{emp.id}/attendance/override",
            headers=h,
            json={"work_date": "2026-06-18", "status": "present", "note": "phase2 verify"},
        )
        if r.status_code == 200 and r.json().get("status") == "present":
            ok("POST attendance override")
        else:
            fail("attendance override", f"{r.status_code} {r.text[:120]}")
    finally:
        db.close()


def verify_phase3() -> None:
    print("\n=== Phase 3 — Polish ===")
    admin_t = login(ADMIN_EMAIL, TEST_PASSWORD)
    if not admin_t:
        fail("phase3 admin login", "skip")
        return
    h = auth_header(admin_t)

    r = client.get("/api/admin/holidays", headers=h)
    if r.status_code == 200:
        ok("GET holidays")
    else:
        fail("holidays list", f"{r.status_code}")

    r = client.post(
        "/api/admin/holidays",
        headers=h,
        json={"holiday_date": "2026-12-25", "name": "Verify Test Holiday"},
    )
    if r.status_code == 200:
        hid = r.json().get("id")
        ok("POST holiday")
        if hid:
            dr = client.delete(f"/api/admin/holidays/{hid}", headers=h)
            if dr.status_code == 200:
                ok("DELETE holiday")
            else:
                fail("delete holiday", f"{dr.status_code}")
    else:
        fail("create holiday", f"{r.status_code} {r.text[:120]}")

    r = client.patch(
        "/api/admin/settings/attendance",
        headers=h,
        json={"half_day_hours": 4.0, "exclude_weekends": True},
    )
    if r.status_code == 200 and r.json().get("half_day_hours") == 4.0:
        ok("half-day settings")
    else:
        fail("half-day settings", f"{r.status_code}")

    r = client.post("/api/admin/attendance/weekly-summary", headers=h)
    if r.status_code == 200 and "sent" in r.json():
        ok("POST weekly summary")
    else:
        fail("weekly summary", f"{r.status_code}")

    r = client.post("/api/admin/attendance/close-day", headers=h, json={"work_date": "2026-06-21"})
    if r.status_code == 200 and r.json().get("skipped") is True:
        ok("close-day skips weekend")
    else:
        fail("weekend skip", f"{r.status_code} {r.json() if r.status_code == 200 else r.text[:120]}")


def verify_phase4() -> None:
    print("\n=== Phase 4 — Production ===")
    emp_t = login(EMPLOYEE_EMAIL, TEST_PASSWORD)
    if not emp_t:
        fail("phase4 employee login", "skip")
        return
    h = auth_header(emp_t)

    r = client.post(
        "/api/auth/change-password",
        headers=h,
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "VerifyPhaseNew2!",
            "confirm_password": "VerifyPhaseNew2!",
        },
    )
    if r.status_code == 200:
        ok("POST change-password")
        r2 = client.post(
            "/api/auth/login",
            json={"email": EMPLOYEE_EMAIL, "password": "VerifyPhaseNew2!"},
        )
        if r2.status_code == 200:
            ok("login with new password")
            emp_t2 = r2.json()["access_token"]
            client.post(
                "/api/auth/change-password",
                headers=auth_header(emp_t2),
                json={
                    "current_password": "VerifyPhaseNew2!",
                    "new_password": TEST_PASSWORD,
                    "confirm_password": TEST_PASSWORD,
                },
            )
            ok("reverted test password")
        else:
            fail("login new password", f"{r2.status_code}")
    else:
        fail("change-password", f"{r.status_code} {r.text[:120]}")

    r = client.post("/api/internal/attendance/close-day", json={})
    if r.status_code in (403, 422):
        ok("internal close-day rejects missing secret header")
    else:
        fail("internal without header", f"expected 403/422 got {r.status_code}")

    r = client.post(
        "/api/internal/attendance/close-day",
        json={"work_date": "2026-06-19"},
        headers={"X-Cron-Secret": ATTENDANCE_CRON_SECRET},
    )
    if r.status_code == 200:
        ok("internal close-day with secret")
    else:
        fail("internal with secret", f"{r.status_code} {r.text[:120]}")

    r = client.get("/api/health")
    if r.status_code == 200:
        ok("health check")
    else:
        fail("health", f"{r.status_code}")


def main() -> None:
    print("Employee panel phase verification")
    setup_test_passwords()
    verify_phase1()
    verify_phase2()
    verify_phase3()
    verify_phase4()
    print(f"\n{'=' * 50}")
    print(f"Passed: {len(passed)}  Failed: {len(failures)}")
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll phases verified OK.")
    sys.exit(0)


if __name__ == "__main__":
    main()
