#!/usr/bin/env python3
"""Full project verification — employee phases + live API smoke (backend must be running)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8000"
ADMIN_EMAIL = "saudakbar65367@gmail.com"
EMPLOYEE_EMAIL = "ameerkhanf22@nutech.edu.pk"
TEST_PASSWORD = "VerifyPhaseTest1!"


def run_employee_phases() -> int:
    print("=== Employee panel phases (in-process) ===")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_employee_phases.py")],
        cwd=ROOT,
    )
    return r.returncode


def live_smoke() -> int:
    print("\n=== Live backend smoke ===")
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {name}" + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(name)

    try:
        httpx.get(f"{BASE}/api/health", timeout=5)
        check("GET /api/health", True)
    except Exception as exc:
        print(f"  FAIL  backend unreachable at {BASE}: {exc}")
        return 1

    login = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    check("admin login", login.status_code == 200, str(login.status_code))
    if login.status_code != 200:
        return 1

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    paths = [
        "/api/dashboard/stats",
        "/api/device/status",
        "/api/admin/employees",
        "/api/admin/notifications/settings",
        "/api/admin/holidays",
        "/api/admin/logs/analytics?days=7",
    ]
    for path in paths:
        r = httpx.get(f"{BASE}{path}", headers=headers, timeout=15)
        check(f"GET {path}", r.status_code == 200, str(r.status_code))

    test = httpx.post(
        f"{BASE}/api/admin/notifications/test-email",
        headers=headers,
        json={},
        timeout=30,
    )
    body = test.json() if test.status_code == 200 else {}
    check(
        "POST /api/admin/notifications/test-email",
        test.status_code == 200 and body.get("sent") is True,
        str(body),
    )

    emp = httpx.post(
        f"{BASE}/api/auth/login",
        json={"email": EMPLOYEE_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    check("employee login", emp.status_code == 200, str(emp.status_code))
    if emp.status_code == 200:
        eh = {"Authorization": f"Bearer {emp.json()['access_token']}"}
        for path in [
            "/api/employee/dashboard",
            "/api/employee/attendance?month=2026-06",
            "/api/employee/company-policy",
        ]:
            r = httpx.get(f"{BASE}{path}", headers=eh, timeout=15)
            check(f"GET {path}", r.status_code == 200, str(r.status_code))

    print()
    if failures:
        print(f"Live smoke failed: {len(failures)} check(s)")
        return 1
    print("Live smoke OK")
    return 0


def main() -> int:
    code = run_employee_phases()
    if code != 0:
        return code
    return live_smoke()


if __name__ == "__main__":
    raise SystemExit(main())
