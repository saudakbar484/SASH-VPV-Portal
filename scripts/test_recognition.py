#!/usr/bin/env python3
"""Recognition smoke test — backend must be running."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
ADMIN_EMAIL = "saudakbar65367@gmail.com"
TEST_PASSWORD = "VerifyPhaseTest1!"


def req(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def main() -> int:
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {name}" + (f" — {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(name)

    print("=== Recognition smoke test ===\n")

    code, health = req("GET", "/api/health")
    check("health", code == 200, str(code))

    code, stream = req("GET", "/api/device/stream-status")
    check("stream-status", code == 200 and stream.get("connected"), str(stream))

    code, dist = req("GET", "/api/hardware/palm-distance")
    check("palm-distance", code == 200, str(dist))
    if isinstance(dist, dict):
        print(f"       distance_mm={dist.get('distance_mm')} in_range={dist.get('in_range')}")

    code, stats = req("GET", "/api/public/stats")
    gallery = stats.get("enrolled_identities", 0) if isinstance(stats, dict) else 0
    check("public gallery stats", code == 200 and gallery > 0, f"gallery={gallery}")

    code, identify = req("POST", "/api/recognize/identify", {"top_k": 5})
    check("identify (no auth)", code == 200, str(code))
    if isinstance(identify, dict):
        print(f"       matched={identify.get('matched')} reason={identify.get('rejected_reason')}")

    code, login = req("POST", "/api/auth/login", {"email": ADMIN_EMAIL, "password": TEST_PASSWORD})
    check("admin login", code == 200, str(login))
    if code != 200:
        return 1
    token = login["access_token"]

    code, identities = req("GET", "/api/admin/registered-identities", token=token)
    check("registered-identities (auth)", code == 200, str(code))
    if isinstance(identities, dict):
        enrolled = sum(
            1 for i in identities.get("identities", [])
            if any(h.get("enrolled") for h in i.get("hands", []))
        )
        print(f"       accounts={identities.get('count')} with_enrolled_hands={enrolled}")

    code, verify = req("POST", "/api/user/verify-palm", token=token)
    check("customer verify-palm with admin token", code == 403, str(verify))

    print()
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
