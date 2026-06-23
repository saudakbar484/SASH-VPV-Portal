"""Simple math captcha for registration."""
from __future__ import annotations

import random
import secrets
import time
from dataclasses import dataclass

CAPTCHA_TTL_S = 300


@dataclass
class CaptchaChallenge:
    captcha_id: str
    question: str
    answer: int
    expires_at: float


_challenges: dict[str, CaptchaChallenge] = {}


def create_captcha() -> dict[str, str]:
    a, b = random.randint(1, 9), random.randint(1, 9)
    cid = secrets.token_urlsafe(12)
    ch = CaptchaChallenge(
        captcha_id=cid,
        question=f"What is {a} + {b}?",
        answer=a + b,
        expires_at=time.time() + CAPTCHA_TTL_S,
    )
    _challenges[cid] = ch
    return {"captcha_id": cid, "question": ch.question}


def verify_captcha(captcha_id: str, answer: int) -> bool:
    ch = _challenges.pop(captcha_id, None)
    if ch is None or time.time() > ch.expires_at:
        return False
    return ch.answer == answer
