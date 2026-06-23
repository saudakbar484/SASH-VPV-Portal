#!/usr/bin/env python3
"""Verify customer portal API endpoints (backend must be running on :8000)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("Customer portal API smoke tests\n")
    try:
        client = httpx.Client(base_url=BASE, timeout=15.0)
    except Exception as exc:
        print(f"Cannot create HTTP client: {exc}")
        return 1

    try:
        r = client.get("/api/health")
        check("health", r.status_code == 200, r.text[:80])
    except httpx.ConnectError:
        print("FAIL — backend not running on :8000")
        return 1

    r = client.get("/api/public/stats")
    check("GET /api/public/stats", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        check("public stats has customers field", "total_customers" in data)

    r = client.post(
        "/api/public/contact",
        json={
            "name": "Verify Script",
            "email": "verify@test.local",
            "subject": "Support",
            "message": "Automated customer portal verification message.",
        },
    )
    check("POST /api/public/contact", r.status_code == 200)

    r = client.get("/api/user/dashboard")
    check("user dashboard requires auth", r.status_code == 401)

    r = client.get("/api/admin/customers")
    check("admin customers requires auth", r.status_code == 401)

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
