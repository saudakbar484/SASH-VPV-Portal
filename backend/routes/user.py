"""Customer / member self-service APIs."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.activity import log_activity
from backend.auth.template_cache import secure_match_for_account
from backend.db import models
from backend.deps import get_db
from backend.deps_auth import require_customer
from backend.device.singleton import get_device, get_fresh_frame
from backend.matcher.singleton import embed_png_bytes
from backend.settings import LOGIN_MATCH_THRESHOLD, USERS_REF_DIR

from xrtech_device import save_frame_png  # noqa: E402

router = APIRouter(prefix="/api/user", tags=["user"])


class CustomerDashboardResponse(BaseModel):
    full_name: str
    email: str
    left_enrolled: bool
    right_enrolled: bool
    last_verification_at: Optional[datetime] = None
    verifications_this_week: int
    member_since: datetime
    security_score: int


class ActivityEntry(BaseModel):
    id: int
    event_type: str
    detail: Optional[str] = None
    created_at: datetime


class CustomerActivityResponse(BaseModel):
    count: int
    activities: list[ActivityEntry]


class CustomerProfileResponse(BaseModel):
    account_id: int
    email: str
    full_name: str
    dataset_id: str
    dataset_name: str
    role: str
    registered_at: datetime
    left_enrolled: bool
    right_enrolled: bool


class PalmVerifyResponse(BaseModel):
    success: bool
    matched: bool
    similarity: float
    threshold: float
    hand: Optional[str] = None
    latency_ms: int
    probe_image_url: Optional[str] = None
    message: Optional[str] = None


def _week_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now - timedelta(days=now.weekday())


@router.get("/dashboard", response_model=CustomerDashboardResponse)
def customer_dashboard(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_customer),
) -> CustomerDashboardResponse:
    week_start = _week_start()
    verify_count = db.execute(
        select(func.count())
        .select_from(models.ActivityLog)
        .where(
            models.ActivityLog.account_id == account.id,
            models.ActivityLog.event_type.in_(("customer_palm_verify", "login", "enrollment_complete")),
            models.ActivityLog.created_at >= week_start,
        )
    ).scalar_one()

    last_verify = db.execute(
        select(models.ActivityLog)
        .where(
            models.ActivityLog.account_id == account.id,
            models.ActivityLog.event_type.in_(("customer_palm_verify", "login")),
        )
        .order_by(models.ActivityLog.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    left_ok = account.left_template is not None
    right_ok = account.right_template is not None
    score = 40
    if left_ok:
        score += 25
    if right_ok:
        score += 25
    if verify_count > 0:
        score += 10

    return CustomerDashboardResponse(
        full_name=account.full_name,
        email=account.email,
        left_enrolled=left_ok,
        right_enrolled=right_ok,
        last_verification_at=last_verify.created_at if last_verify else None,
        verifications_this_week=int(verify_count or 0),
        member_since=account.created_at,
        security_score=min(100, score),
    )


@router.get("/profile", response_model=CustomerProfileResponse)
def customer_profile(
    account: models.Account = Depends(require_customer),
) -> CustomerProfileResponse:
    return CustomerProfileResponse(
        account_id=account.id,
        email=account.email,
        full_name=account.full_name,
        dataset_id=account.dataset_id,
        dataset_name=account.dataset_name,
        role=account.role,
        registered_at=account.created_at,
        left_enrolled=account.left_template is not None,
        right_enrolled=account.right_template is not None,
    )


@router.get("/activity", response_model=CustomerActivityResponse)
def customer_activity(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_customer),
) -> CustomerActivityResponse:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(models.ActivityLog)
        .where(
            models.ActivityLog.account_id == account.id,
            models.ActivityLog.created_at >= since,
        )
        .order_by(models.ActivityLog.created_at.desc())
        .limit(200)
    ).scalars().all()
    return CustomerActivityResponse(
        count=len(rows),
        activities=[
            ActivityEntry(
                id=a.id,
                event_type=a.event_type,
                detail=a.detail,
                created_at=a.created_at,
            )
            for a in rows
        ],
    )


@router.post("/verify-palm", response_model=PalmVerifyResponse)
def verify_palm(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_customer),
) -> PalmVerifyResponse:
    t0 = time.perf_counter()
    device = get_device()
    if not device.is_connected():
        raise HTTPException(status_code=503, detail="Scanner not connected")

    raw = get_fresh_frame()
    if not raw:
        return PalmVerifyResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            message="No palm detected — hold hand 3–8 cm above the sensor",
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    probe_path = USERS_REF_DIR / "_captures" / f"verify_{account.id}_{ts}.png"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    save_frame_png(raw, probe_path)
    probe = embed_png_bytes(raw)
    probe_url = f"/api/auth/login/probe?file={probe_path.name}"

    match = secure_match_for_account(probe, account.id)
    matched = match.matched
    best_hand = match.hand
    best_sim = match.similarity
    latency_ms = int((time.perf_counter() - t0) * 1000)

    if matched:
        log_activity(
            db,
            account_id=account.id,
            event_type="customer_palm_verify",
            detail=f"hand={best_hand};similarity={best_sim:.4f}",
            commit=True,
        )
        return PalmVerifyResponse(
            success=True,
            matched=True,
            similarity=float(best_sim),
            threshold=match.threshold,
            hand=best_hand,
            latency_ms=latency_ms,
            probe_image_url=probe_url,
            message=f"Identity verified — {best_hand} hand matched",
        )

    log_activity(
        db,
        account_id=account.id,
        event_type="customer_palm_verify_failed",
        detail=f"similarity={best_sim:.4f}",
        commit=True,
    )
    return PalmVerifyResponse(
        success=False,
        matched=False,
        similarity=float(max(0.0, best_sim)),
        threshold=match.threshold,
        latency_ms=latency_ms,
        probe_image_url=probe_url,
        message=match.reason or f"Verification failed — similarity {best_sim:.3f} (need {match.threshold})",
    )


@router.delete("/account")
def delete_account_request(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_customer),
) -> dict:
    log_activity(
        db,
        account_id=account.id,
        event_type="account_deletion_requested",
        detail="customer_requested",
        commit=True,
    )
    return {"success": True, "message": "Deletion request recorded. An administrator will process your request."}
