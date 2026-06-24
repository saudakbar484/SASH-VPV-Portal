"""/api/recognize/* - 1:1 verify, 1:N identify, recognition log query.

The neural matcher (EfficientNet-B0 + CBAM + ArcFace-trained head) produces
L2-normalised 512-d embeddings, so cosine similarity is just a dot product.
The accept/reject threshold is the production EER threshold from
`palm_vein.deployment.DEFAULT_THRESHOLD` (0.40).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.db import models
from backend.db.schemas import (
    IdentifyCandidate,
    IdentifyRequest,
    IdentifyResponse,
    RecognitionLogEntry,
    RecognitionLogsResponse,
    VerifyRequest,
    VerifyResponse,
)
from backend.deps import get_db
from backend.device.singleton import get_device, get_fresh_frame
from backend.matcher.secure_match import evaluate_gallery_match
from backend.matcher.singleton import embed_image, embed_png_bytes
from backend.settings import (
    CAPTURES_DIR,
    DEFAULT_THRESHOLD,
    EMBEDDING_DIM,
    LOGIN_MATCH_MIN_MARGIN,
    RECOGNITION_LOGS_ENABLED,
)
from backend.utils.embeddings import bytes_to_embedding

from xrtech_device import save_frame_png  # noqa: E402

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recognize", tags=["recognize"])

RECOGNIZE_CAPTURES = CAPTURES_DIR / "recognize"
RECOGNIZE_CAPTURES.mkdir(parents=True, exist_ok=True)


def _confidence(similarity: float, threshold: float = DEFAULT_THRESHOLD) -> float:
    """Map cosine sim -> 0..100 confidence; 0 at threshold, 100 at sim=1.0."""
    if similarity >= 1.0:
        return 100.0
    raw = (similarity - threshold) / max(1e-8, 1.0 - threshold) * 100.0
    return float(max(0.0, min(100.0, raw)))


def _grab_probe_frame() -> tuple[Optional[Path], Optional[bytes]]:
    """Capture one live frame; return (saved path, raw bytes) for recognition."""
    device = get_device()
    if not device.is_connected():
        return None, None
    raw = get_fresh_frame(max_wait_s=1.5)
    if not raw:
        return None, None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = RECOGNIZE_CAPTURES / f"probe_{ts}.png"
    try:
        save_frame_png(raw, path)
    except Exception as e:
        logger.warning("save_frame_png failed: %s", e)
        return None, None
    return path, raw


def _insert_log(
    db: Session,
    *,
    mode: str,
    user_id: Optional[int],
    claimed_name: Optional[str],
    matched_name: Optional[str],
    similarity: float,
    matched: bool,
    latency_ms: int,
) -> models.RecognitionLog | None:
    if not RECOGNITION_LOGS_ENABLED:
        return None
    row = models.RecognitionLog(
        user_id=user_id,
        mode=mode,
        claimed_name=claimed_name,
        matched_name=matched_name,
        similarity=similarity,
        matched=matched,
        threshold=DEFAULT_THRESHOLD,
        latency_ms=latency_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _resolve_verify_users(body: VerifyRequest, db: Session) -> tuple[list[models.User], str]:
    """Return candidate User rows and the display name for the claimed identity."""
    if body.account_id is not None:
        account = db.get(models.Account, body.account_id)
        if account is None:
            raise HTTPException(status_code=404, detail=f"Account id={body.account_id} not found")
        users = db.execute(
            select(models.User).where(models.User.name == account.dataset_name)
        ).scalars().all()
        if not users:
            raise HTTPException(
                status_code=404,
                detail=f"No enrolled templates for account '{account.full_name}'",
            )
        return users, account.full_name

    if body.user_id is not None:
        user = db.get(models.User, body.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail=f"User id={body.user_id} not enrolled")
        return [user], user.name

    if body.name:
        user = db.execute(
            select(models.User).where(models.User.name == body.name)
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail=f"User '{body.name}' not enrolled")
        return [user], user.name

    raise HTTPException(status_code=400, detail="Provide account_id, user_id, or name")


@router.post("/verify", response_model=VerifyResponse)
def verify(body: VerifyRequest, db: Session = Depends(get_db)) -> VerifyResponse:
    """1:1 verification: claim an account or user, prove it with a live capture."""
    users, claimed_name = _resolve_verify_users(body, db)
    user = users[0]

    t0 = time.perf_counter()
    captured_at = datetime.now(timezone.utc)

    probe_path, raw = _grab_probe_frame()
    if probe_path is None or raw is None:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        row = _insert_log(
            db,
            mode="verify",
            user_id=user.id,
            claimed_name=claimed_name,
            matched_name=None,
            similarity=0.0,
            matched=False,
            latency_ms=latency_ms,
        )
        return VerifyResponse(
            matched=False,
            similarity=0.0,
            threshold=DEFAULT_THRESHOLD,
            confidence=0.0,
            user_id=user.id,
            claimed_name=claimed_name,
            hand=user.hand,
            latency_ms=latency_ms,
            captured_at=captured_at,
            log_id=row.id if row else 0,
            rejected_reason="No frame from sensor - place palm and retry",
        )

    try:
        probe_emb = embed_png_bytes(raw)
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        row = _insert_log(
            db,
            mode="verify",
            user_id=user.id,
            claimed_name=claimed_name,
            matched_name=None,
            similarity=0.0,
            matched=False,
            latency_ms=latency_ms,
        )
        return VerifyResponse(
            matched=False,
            similarity=0.0,
            threshold=DEFAULT_THRESHOLD,
            confidence=0.0,
            user_id=user.id,
            claimed_name=claimed_name,
            hand=user.hand,
            latency_ms=latency_ms,
            captured_at=captured_at,
            log_id=row.id if row else 0,
            probe_image_path=str(probe_path),
            rejected_reason=str(e),
        )

    all_users = db.execute(select(models.User).order_by(models.User.id)).scalars().all()
    if not all_users:
        raise HTTPException(status_code=404, detail="No enrolled templates in gallery")

    templates = np.stack([bytes_to_embedding(u.template_embedding) for u in all_users])
    probe_vec = probe_emb.reshape(-1)
    sims = templates @ probe_vec
    claimed_ids = {u.id for u in users}

    matched, similarity, second_sim, margin, reject_reason = evaluate_gallery_match(
        probe_vec,
        sims,
        threshold=DEFAULT_THRESHOLD,
        min_margin=LOGIN_MATCH_MIN_MARGIN,
    )
    best_idx = int(np.argmax(sims))
    best_user = all_users[best_idx]
    if matched and best_user.id not in claimed_ids:
        matched = False
        reject_reason = (
            f"Best gallery match ({best_user.name} {best_user.hand}) "
            f"does not match claimed identity"
        )
    elif not matched:
        similarity = float(sims[best_idx])
        best_user = all_users[best_idx]
    confidence = _confidence(similarity)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    row = _insert_log(
        db,
        mode="verify",
        user_id=best_user.id,
        claimed_name=claimed_name,
        matched_name=claimed_name if matched else None,
        similarity=similarity,
        matched=matched,
        latency_ms=latency_ms,
    )
    logger.info(
        "Verify claimed=%s hand=%s sim=%.4f second=%.4f margin=%.4f thr=%.4f matched=%s latency=%dms%s",
        claimed_name, best_user.hand, similarity, second_sim, margin, DEFAULT_THRESHOLD, matched, latency_ms,
        f" reason={reject_reason}" if reject_reason else "",
    )
    return VerifyResponse(
        matched=matched,
        similarity=similarity,
        threshold=DEFAULT_THRESHOLD,
        confidence=confidence,
        user_id=best_user.id,
        claimed_name=claimed_name,
        hand=best_user.hand,
        latency_ms=latency_ms,
        captured_at=captured_at,
        log_id=row.id if row else 0,
        probe_image_path=str(probe_path),
        rejected_reason=reject_reason,
    )


@router.post("/identify", response_model=IdentifyResponse)
def identify(body: IdentifyRequest, db: Session = Depends(get_db)) -> IdentifyResponse:
    """1:N identification across all enrolled users; returns top-K candidates."""
    users = db.execute(select(models.User).order_by(models.User.id)).scalars().all()
    gallery_size = len(users)

    t0 = time.perf_counter()
    captured_at = datetime.now(timezone.utc)

    if gallery_size == 0:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        row = _insert_log(
            db, mode="identify", user_id=None, claimed_name=None,
            matched_name=None, similarity=0.0, matched=False, latency_ms=latency_ms,
        )
        return IdentifyResponse(
            matched=False, threshold=DEFAULT_THRESHOLD, gallery_size=0,
            latency_ms=latency_ms, captured_at=captured_at, log_id=row.id,
            rejected_reason="No users enrolled - run enrollment first",
        )

    probe_path, raw = _grab_probe_frame()
    if probe_path is None or raw is None:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        row = _insert_log(
            db, mode="identify", user_id=None, claimed_name=None,
            matched_name=None, similarity=0.0, matched=False, latency_ms=latency_ms,
        )
        return IdentifyResponse(
            matched=False, threshold=DEFAULT_THRESHOLD, gallery_size=gallery_size,
            latency_ms=latency_ms, captured_at=captured_at, log_id=row.id,
            rejected_reason="No frame from sensor - place palm and retry",
        )

    try:
        probe_emb = embed_png_bytes(raw)
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        row = _insert_log(
            db, mode="identify", user_id=None, claimed_name=None,
            matched_name=None, similarity=0.0, matched=False, latency_ms=latency_ms,
        )
        return IdentifyResponse(
            matched=False, threshold=DEFAULT_THRESHOLD, gallery_size=gallery_size,
            latency_ms=latency_ms, captured_at=captured_at, log_id=row.id,
            probe_image_path=str(probe_path), rejected_reason=str(e),
        )

    templates = np.stack(
        [bytes_to_embedding(u.template_embedding) for u in users]
    )
    if templates.shape[1] != EMBEDDING_DIM:
        raise HTTPException(
            status_code=500,
            detail=f"Gallery dim mismatch: {templates.shape[1]} vs {EMBEDDING_DIM}",
        )

    probe_vec = probe_emb.reshape(-1)
    sims = templates @ probe_vec  # cosine since both sides unit-normalised
    order = np.argsort(-sims)
    top_k = min(body.top_k, len(users))
    candidates = [
        IdentifyCandidate(
            user_id=users[int(i)].id,
            name=users[int(i)].name,
            hand=users[int(i)].hand,
            similarity=float(sims[int(i)]),
            confidence=_confidence(float(sims[int(i)])),
        )
        for i in order[:top_k]
    ]
    best = candidates[0]
    matched, _, second_sim, margin, reject_reason = evaluate_gallery_match(
        probe_vec,
        sims,
        threshold=DEFAULT_THRESHOLD,
        min_margin=LOGIN_MATCH_MIN_MARGIN,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    row = _insert_log(
        db,
        mode="identify",
        user_id=best.user_id if matched else None,
        claimed_name=None,
        matched_name=best.name if matched else None,
        similarity=best.similarity,
        matched=matched,
        latency_ms=latency_ms,
    )
    logger.info(
        "Identify best=%s sim=%.4f second=%.4f margin=%.4f thr=%.4f matched=%s gallery=%d latency=%dms%s",
        best.name,
        best.similarity,
        second_sim,
        margin,
        DEFAULT_THRESHOLD,
        matched,
        gallery_size,
        latency_ms,
        f" reason={reject_reason}" if reject_reason else "",
    )

    return IdentifyResponse(
        matched=matched,
        best_match=best if matched else None,
        candidates=candidates,
        threshold=DEFAULT_THRESHOLD,
        gallery_size=gallery_size,
        latency_ms=latency_ms,
        captured_at=captured_at,
        log_id=row.id if row else 0,
        probe_image_path=str(probe_path),
        rejected_reason=reject_reason,
    )


@router.get("/logs", response_model=RecognitionLogsResponse)
def list_logs(
    mode: Optional[str] = Query(None, pattern="^(verify|identify)$"),
    user_id: Optional[int] = Query(None),
    matched: Optional[bool] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> RecognitionLogsResponse:
    if not RECOGNITION_LOGS_ENABLED:
        return RecognitionLogsResponse(
            count=0,
            accepted=0,
            rejected=0,
            limit=limit,
            offset=offset,
            logs=[],
            enabled=False,
        )
    conds = []
    if mode:
        conds.append(models.RecognitionLog.mode == mode)
    if user_id is not None:
        conds.append(models.RecognitionLog.user_id == user_id)
    if matched is not None:
        conds.append(models.RecognitionLog.matched.is_(matched))
    if since is not None:
        conds.append(models.RecognitionLog.created_at >= since)
    if until is not None:
        conds.append(models.RecognitionLog.created_at <= until)
    where_clause = and_(*conds) if conds else True

    count = db.execute(
        select(func.count(models.RecognitionLog.id)).where(where_clause)
    ).scalar_one()
    accepted = db.execute(
        select(func.count(models.RecognitionLog.id)).where(
            and_(where_clause, models.RecognitionLog.matched.is_(True))
        )
    ).scalar_one()
    rejected = count - accepted

    rows = db.execute(
        select(models.RecognitionLog)
        .where(where_clause)
        .order_by(models.RecognitionLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return RecognitionLogsResponse(
        count=count,
        accepted=accepted,
        rejected=rejected,
        limit=limit,
        offset=offset,
        logs=[RecognitionLogEntry.model_validate(r) for r in rows],
    )
