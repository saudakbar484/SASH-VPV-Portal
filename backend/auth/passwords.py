"""Password hashing helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(plain: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        scheme, salt, digest_hex = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)
