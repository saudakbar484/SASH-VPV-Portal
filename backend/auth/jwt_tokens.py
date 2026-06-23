"""Minimal signed session tokens (no external JWT dependency)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from backend.settings import AUTH_SECRET, AUTH_TOKEN_TTL_S


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_access_token(account_id: int, email: str) -> str:
    payload = {
        "sub": account_id,
        "email": email,
        "exp": int(time.time()) + AUTH_TOKEN_TTL_S,
    }
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        body, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url(expected), sig):
        return None
    try:
        payload = json.loads(_b64url_decode(body))
    except (json.JSONDecodeError, ValueError):
        return None
    if int(payload.get("exp", 0)) < time.time():
        return None
    return payload
