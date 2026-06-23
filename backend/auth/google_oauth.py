"""Verify Google Identity Services ID tokens."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from backend.settings import GOOGLE_CLIENT_ID

logger = logging.getLogger(__name__)


def verify_google_credential(credential: str) -> dict[str, Any]:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on this server")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
    except ImportError as exc:
        logger.error("google-auth package missing: %s", exc)
        raise HTTPException(status_code=503, detail="Google sign-in is unavailable") from exc

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token") from exc

    if idinfo.get("email_verified") is False:
        raise HTTPException(status_code=401, detail="Google email is not verified")

    email = (idinfo.get("email") or "").strip().lower()
    sub = (idinfo.get("sub") or "").strip()
    if not email or not sub:
        raise HTTPException(status_code=401, detail="Google account is missing required profile fields")

    return {
        "email": email,
        "sub": sub,
        "full_name": (idinfo.get("name") or email.split("@")[0]).strip(),
    }
