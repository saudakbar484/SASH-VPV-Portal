"""/api/enroll/session/* - multi-capture enrollment flow."""
from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import models
from backend.deps import get_db
from backend.device.singleton import get_device, get_fresh_frame
from backend.matcher.singleton import embed_image
from backend.settings import EMBEDDING_DIM, USERS_REF_DIR
from backend.utils.embeddings import average_and_normalise, embedding_to_bytes

# xrtech_device added to sys.path by backend.settings
from xrtech_device import save_frame_png  # noqa: E402

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enroll", tags=["enroll"])

ENROLL_TMP_ROOT = USERS_REF_DIR / "_enroll_sessions"
MIN_TARGET_CAPTURES = 3
MAX_TARGET_CAPTURES = 15


class StartRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    hand: Literal["Left", "Right"]
    target_count: int = Field(
        default=5, ge=MIN_TARGET_CAPTURES, le=MAX_TARGET_CAPTURES
    )


class SessionRefRequest(BaseModel):
    session_id: str


class SessionStatus(BaseModel):
    session_id: str
    name: str
    hand: str
    target_count: int
    captured_count: int
    attempts: int
    last_error: Optional[str] = None
    finished: bool
    created_at: datetime


class CaptureResponse(SessionStatus):
    captured: bool
    reason: Optional[str] = None
    last_image_path: Optional[str] = None


class FinishResponse(BaseModel):
    success: bool
    user_id: int
    name: str
    hand: str
    sample_count: int
    template_dim: int


class _EnrollSession:
    """In-memory state for a single enrollment session."""

    def __init__(self, name: str, hand: str, target_count: int) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.hand = hand
        self.target_count = target_count
        self.embeddings: list[np.ndarray] = []
        self.image_paths: list[Path] = []
        self.attempts = 0
        self.last_error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.tmp_dir = ENROLL_TMP_ROOT / self.id / hand
        self.tmp_dir.mkdir(parents=True, exist_ok=True)


_sessions: dict[str, _EnrollSession] = {}
_sessions_lock = Lock()


def _get_session(session_id: str) -> _EnrollSession:
    with _sessions_lock:
        sess = _sessions.get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return sess


def _status_payload(sess: _EnrollSession, finished: bool = False) -> dict:
    return dict(
        session_id=sess.id,
        name=sess.name,
        hand=sess.hand,
        target_count=sess.target_count,
        captured_count=len(sess.embeddings),
        attempts=sess.attempts,
        last_error=sess.last_error,
        finished=finished,
        created_at=sess.created_at,
    )


@router.post("/session/start", response_model=SessionStatus)
def start_session(body: StartRequest, db: Session = Depends(get_db)) -> SessionStatus:
    existing = db.execute(
        select(models.User).where(models.User.name == body.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Identity '{body.name}' already enrolled (id={existing.id})",
        )
    sess = _EnrollSession(body.name, body.hand, body.target_count)
    with _sessions_lock:
        _sessions[sess.id] = sess
    logger.info(
        "Enroll session %s started: name=%s hand=%s target=%s",
        sess.id, body.name, body.hand, body.target_count,
    )
    return SessionStatus(**_status_payload(sess))


@router.post("/session/capture", response_model=CaptureResponse)
def capture(body: SessionRefRequest) -> CaptureResponse:
    sess = _get_session(body.session_id)
    sess.attempts += 1

    device = get_device()
    if not device.is_connected():
        sess.last_error = "Sensor not connected"
        return CaptureResponse(captured=False, reason=sess.last_error, **_status_payload(sess))

    raw = get_fresh_frame()
    if not raw:
        sess.last_error = "No frame - place palm 3-8 cm above the sensor and retry"
        return CaptureResponse(captured=False, reason=sess.last_error, **_status_payload(sess))

    idx = len(sess.image_paths) + 1
    tmp_path = sess.tmp_dir / f"{idx:02d}.png"
    try:
        save_frame_png(raw, tmp_path)
    except Exception as e:
        sess.last_error = f"Failed to save PNG: {e}"
        return CaptureResponse(captured=False, reason=sess.last_error, **_status_payload(sess))

    try:
        emb = embed_image(tmp_path)
    except Exception as e:
        sess.last_error = str(e)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return CaptureResponse(captured=False, reason=sess.last_error, **_status_payload(sess))

    sess.embeddings.append(emb)
    sess.image_paths.append(tmp_path)
    sess.last_error = None
    logger.info(
        "Capture ok: session=%s idx=%s/%s emb_norm=%.4f",
        sess.id, len(sess.embeddings), sess.target_count, float(np.linalg.norm(emb)),
    )
    return CaptureResponse(
        captured=True,
        last_image_path=str(tmp_path),
        **_status_payload(sess),
    )


@router.post("/session/finish", response_model=FinishResponse)
def finish(body: SessionRefRequest, db: Session = Depends(get_db)) -> FinishResponse:
    sess = _get_session(body.session_id)
    n = len(sess.embeddings)
    if n < MIN_TARGET_CAPTURES:
        raise HTTPException(
            status_code=400,
            detail=f"Need >= {MIN_TARGET_CAPTURES} successful captures, have {n}",
        )

    if db.execute(
        select(models.User).where(models.User.name == sess.name)
    ).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Identity '{sess.name}' was enrolled in another session - cancel this one",
        )

    template = average_and_normalise(sess.embeddings)
    if template.shape != (EMBEDDING_DIM,):
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected template shape {template.shape}",
        )

    user = models.User(
        name=sess.name,
        hand=sess.hand,
        template_embedding=embedding_to_bytes(template),
    )
    db.add(user)
    db.flush()  # populate user.id

    final_dir = USERS_REF_DIR / str(user.id) / sess.hand
    final_dir.mkdir(parents=True, exist_ok=True)
    for i, (emb, src_path) in enumerate(zip(sess.embeddings, sess.image_paths), start=1):
        dst = final_dir / f"{i:02d}.png"
        try:
            shutil.move(str(src_path), str(dst))
        except Exception:
            try:
                shutil.copy2(str(src_path), str(dst))
            except Exception as e:
                logger.warning("Could not move/copy %s -> %s: %s", src_path, dst, e)
                continue
        db.add(
            models.EnrollmentSample(
                user_id=user.id,
                image_path=str(dst),
                embedding=embedding_to_bytes(emb),
            )
        )

    db.commit()
    db.refresh(user)

    shutil.rmtree(ENROLL_TMP_ROOT / sess.id, ignore_errors=True)
    with _sessions_lock:
        _sessions.pop(sess.id, None)

    logger.info(
        "Enrolled user id=%s name=%s hand=%s samples=%s",
        user.id, user.name, user.hand, n,
    )
    return FinishResponse(
        success=True,
        user_id=user.id,
        name=user.name,
        hand=user.hand,
        sample_count=n,
        template_dim=EMBEDDING_DIM,
    )


@router.post("/session/cancel")
def cancel(body: SessionRefRequest) -> dict:
    sess = _get_session(body.session_id)
    shutil.rmtree(ENROLL_TMP_ROOT / sess.id, ignore_errors=True)
    with _sessions_lock:
        _sessions.pop(sess.id, None)
    logger.info("Cancelled enroll session %s", sess.id)
    return {"success": True, "session_id": sess.id}


@router.get("/session/{session_id}/status", response_model=SessionStatus)
def session_status(session_id: str) -> SessionStatus:
    sess = _get_session(session_id)
    return SessionStatus(**_status_payload(sess))


@router.get("/sessions", response_model=list[SessionStatus])
def list_sessions() -> list[SessionStatus]:
    with _sessions_lock:
        items = list(_sessions.values())
    return [SessionStatus(**_status_payload(s)) for s in items]


class LookupMatch(BaseModel):
    name: str
    folder_id: Optional[str] = None
    source: str
    left_samples: int = 0
    right_samples: int = 0
    left_enrolled: bool = False
    right_enrolled: bool = False
    account_email: Optional[str] = None
    match_type: str  # exact | partial | similar


class EnrollLookupResponse(BaseModel):
    query: str
    exact_match: Optional[LookupMatch] = None
    similar: list[LookupMatch] = []
    message: Optional[str] = None
    can_enroll_left: bool = True
    can_enroll_right: bool = True


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _lookup_match(db: Session, name: str, match_type: str) -> LookupMatch:
    from backend.auth.folder_mapping import read_rows

    folder_id = None
    account_email = None
    source = "admin"
    for row in read_rows():
        if _norm(row.get("dataset_name", "")) == _norm(name):
            folder_id = row.get("folder_id")
            account_email = row.get("email")
            source = "registered"
            break

    left = db.execute(
        select(models.User).where(models.User.name == name, models.User.hand == "Left")
    ).scalar_one_or_none()
    right = db.execute(
        select(models.User).where(models.User.name == name, models.User.hand == "Right")
    ).scalar_one_or_none()

    return LookupMatch(
        name=name,
        folder_id=folder_id,
        source=source,
        left_samples=len(left.samples) if left else 0,
        right_samples=len(right.samples) if right else 0,
        left_enrolled=left is not None,
        right_enrolled=right is not None,
        account_email=account_email,
        match_type=match_type,
    )


@router.get("/lookup", response_model=EnrollLookupResponse)
def enroll_lookup(
    q: str = Query(..., min_length=1, max_length=128),
    db: Session = Depends(get_db),
) -> EnrollLookupResponse:
    query = q.strip()
    qn = _norm(query)

    accounts = db.execute(select(models.Account)).scalars().all()
    admin_users = db.execute(select(models.User.name).distinct()).scalars().all()
    all_names = {a.dataset_name for a in accounts} | set(admin_users)

    exact = next((n for n in all_names if _norm(n) == qn), None)
    if exact:
        m = _lookup_match(db, exact, "exact")
        return EnrollLookupResponse(
            query=query,
            exact_match=m,
            similar=[],
            message=f"'{exact}' is already in the system.",
            can_enroll_left=not m.left_enrolled,
            can_enroll_right=not m.right_enrolled,
        )

    partial = [n for n in all_names if qn in _norm(n) or _norm(n) in qn]
    partial = sorted(set(partial), key=len)[:5]

    similar: list[LookupMatch] = []
    message = None
    if partial:
        similar = [_lookup_match(db, n, "partial") for n in partial]
        best = partial[0]
        message = (
            f"No exact match for '{query}'. Did you mean '{best}'? "
            f"{'Other similar names were also found.' if len(partial) > 1 else ''}"
        )
    else:
        message = f"No existing dataset for '{query}'. You can enroll as a new identity."

    return EnrollLookupResponse(
        query=query,
        exact_match=None,
        similar=similar,
        message=message,
        can_enroll_left=True,
        can_enroll_right=True,
    )
