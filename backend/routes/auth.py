"""/api/auth/* — signup, login (password + palm), captcha."""
from __future__ import annotations

import logging
import re
import shutil
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.activity import end_session, log_activity, start_session
from backend.auth.attendance import get_settings
from backend.auth.captcha import create_captcha, verify_captcha
from backend.auth.google_oauth import verify_google_credential
from backend.auth.folder_mapping import email_exists, next_folder_id
from backend.auth.email_verification import issue_verification_code, verify_email_code
from backend.auth.password_reset import issue_password_reset_code, reset_password_with_code
from backend.auth.registration import (
    account_exists_for_dataset,
    clear_orphan_users,
    complete_account_palm_enrollment,
    persist_customer_account,
    persist_registration,
    username_taken,
)
from backend.auth.invites import get_valid_invite, mark_invite_used
from backend.auth.template_cache import match_probe, resolve_account, secure_match_for_account, secure_match_probe
from backend.auth.jwt_tokens import create_access_token
from backend.auth.passwords import hash_password, verify_password
from backend.db import models
from backend.deps import get_db
from backend.deps_auth import get_current_account, require_customer
from backend.device.singleton import get_device, get_fresh_frame
from backend.matcher.singleton import embed_image, embed_png_bytes
from backend.settings import (
    DEFAULT_THRESHOLD,
    LOGIN_MATCH_MIN_MARGIN,
    LOGIN_MATCH_THRESHOLD,
    EMBEDDING_DIM,
    GOOGLE_CLIENT_ID,
    USERS_REF_DIR,
)
from backend.utils.embeddings import bytes_to_embedding

from xrtech_device import save_frame_png  # noqa: E402

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

CAPTURES_PER_HAND = 10
REGISTER_TMP = USERS_REF_DIR / "_register_sessions"


class CaptchaResponse(BaseModel):
    captcha_id: str
    question: str


class RegisterStartRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=256)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    captcha_id: str
    captcha_answer: int
    invite_token: Optional[str] = Field(default=None, max_length=128)


class RegisterStartResponse(BaseModel):
    register_session_id: Optional[str] = None
    message: str
    email: Optional[str] = None
    verification_required: bool = False
    email_sent: bool = False


class CustomerRegisterStartRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    captcha_id: str
    captcha_answer: int


class CustomerVerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class CustomerResendVerificationRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class CustomerSignInOptionsResponse(BaseModel):
    exists: bool
    email_verified: bool = False
    palms_enrolled: bool = False
    username: Optional[str] = None


class RegisterPalmStartRequest(BaseModel):
    register_session_id: str
    dataset_name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    first_hand: Literal["Left", "Right"]


class RegisterEnrollStartRequest(BaseModel):
    first_hand: Literal["Left", "Right"]


class RegisterSessionStatus(BaseModel):
    register_session_id: str
    full_name: str
    email: str
    dataset_name: str
    folder_id: str
    current_hand: str
    left_captured: int
    right_captured: int
    target_per_hand: int
    left_complete: bool
    right_complete: bool
    both_complete: bool
    last_error: Optional[str] = None


class RegisterCaptureRequest(BaseModel):
    register_session_id: str


class RegisterCaptureResponse(RegisterSessionStatus):
    captured: bool
    reason: Optional[str] = None
    last_capture_index: Optional[int] = None
    last_capture_hand: Optional[str] = None
    last_image_url: Optional[str] = None
    embedding_norm: Optional[float] = None
    message: Optional[str] = None


class RegisterSwitchHandRequest(BaseModel):
    register_session_id: str
    next_hand: Literal["Left", "Right"]


class RegisterCompleteResponse(BaseModel):
    success: bool
    account_id: int
    email: str
    full_name: str
    dataset_id: str
    dataset_name: str
    access_token: Optional[str] = None
    token_type: str = "bearer"
    role: str = "employee"
    session_id: Optional[int] = None
    verification_required: bool = False
    email_sent: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PalmLoginResponse(BaseModel):
    success: bool
    matched: bool
    similarity: float
    threshold: float
    access_token: Optional[str] = None
    token_type: str = "bearer"
    account_id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    hand: Optional[str] = None
    latency_ms: int
    probe_image_url: Optional[str] = None
    message: Optional[str] = None
    role: Optional[str] = None
    session_id: Optional[int] = None


class AuthUserResponse(BaseModel):
    account_id: int
    email: str
    full_name: str
    dataset_id: str
    dataset_name: str
    role: str = "employee"
    session_id: Optional[int] = None


class InvitePreviewResponse(BaseModel):
    valid: bool
    full_name: Optional[str] = None
    email: Optional[str] = None
    expires_at: Optional[datetime] = None
    message: Optional[str] = None


class PalmLogoutResponse(BaseModel):
    success: bool
    matched: bool
    similarity: float
    threshold: float
    message: Optional[str] = None
    probe_image_url: Optional[str] = None


class LogoutRequest(BaseModel):
    session_id: Optional[int] = None
    email_fallback: bool = False
    password: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=10)
    intent: Literal["login", "signup"]


class GoogleAuthResponse(BaseModel):
    status: Literal["authenticated", "needs_enrollment"]
    access_token: Optional[str] = None
    account_id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    role: Optional[str] = None
    session_id: Optional[int] = None
    register_session_id: Optional[str] = None
    message: Optional[str] = None


class GoogleConfigResponse(BaseModel):
    enabled: bool
    client_id: Optional[str] = None


class _RegisterSession:
    def __init__(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        invite_id: Optional[int],
        role: str = "employee",
        google_sub: Optional[str] = None,
        existing_account_id: Optional[int] = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.full_name = full_name
        self.email = email.lower()
        self.password_hash = password_hash
        self.invite_id = invite_id
        self.role = role
        self.google_sub = google_sub
        self.existing_account_id = existing_account_id
        self.dataset_name = ""
        self.folder_id = ""
        self.current_hand: Literal["Left", "Right"] = "Left"
        self.left_embeddings: list[np.ndarray] = []
        self.right_embeddings: list[np.ndarray] = []
        self.left_paths: list[Path] = []
        self.right_paths: list[Path] = []
        self.last_error: Optional[str] = None
        self.palm_started = False
        self.tmp_root = REGISTER_TMP / self.id

    @property
    def left_complete(self) -> bool:
        return len(self.left_embeddings) >= CAPTURES_PER_HAND

    @property
    def right_complete(self) -> bool:
        return len(self.right_embeddings) >= CAPTURES_PER_HAND

    @property
    def both_complete(self) -> bool:
        return self.left_complete and self.right_complete


_sessions: dict[str, _RegisterSession] = {}
_lock = Lock()


def _get_reg(session_id: str) -> _RegisterSession:
    with _lock:
        s = _sessions.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Registration session not found")
    return s


def _login_response(db: Session, account: models.Account, login_method: str) -> dict:
    token = create_access_token(account.id, account.email)
    auth_sess = start_session(db, account_id=account.id, login_method=login_method)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": AuthUserResponse(
            account_id=account.id,
            email=account.email,
            full_name=account.full_name,
            dataset_id=account.dataset_id,
            dataset_name=account.dataset_name,
            role=account.role,
            session_id=auth_sess.id,
        ),
    }


def _embed_live_probe(prefix: str = "login") -> tuple[Optional[np.ndarray], Optional[str]]:
    """Capture scanner frame, persist probe PNG for UI, return embedding + probe URL."""
    raw = get_fresh_frame()
    if not raw:
        return None, None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    probe_path = USERS_REF_DIR / "_captures" / f"{prefix}_{ts}.png"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    save_frame_png(raw, probe_path)
    probe_url = f"/api/auth/login/probe?file={probe_path.name}"
    try:
        probe = embed_png_bytes(raw)
    except Exception as exc:
        logger.warning("Probe embedding failed: %s", exc)
        raise
    return probe, probe_url


def _status(sess: _RegisterSession) -> dict:
    return dict(
        register_session_id=sess.id,
        full_name=sess.full_name,
        email=sess.email,
        dataset_name=sess.dataset_name,
        folder_id=sess.folder_id,
        current_hand=sess.current_hand,
        left_captured=len(sess.left_embeddings),
        right_captured=len(sess.right_embeddings),
        target_per_hand=CAPTURES_PER_HAND,
        left_complete=sess.left_complete,
        right_complete=sess.right_complete,
        both_complete=sess.both_complete,
        last_error=sess.last_error,
    )


@router.get("/invite/{token}", response_model=InvitePreviewResponse)
def preview_invite(token: str, db: Session = Depends(get_db)) -> InvitePreviewResponse:
    invite = get_valid_invite(db, token)
    if invite is None:
        return InvitePreviewResponse(
            valid=False,
            message="Invite is invalid, expired, or already used — contact HR.",
        )
    return InvitePreviewResponse(
        valid=True,
        full_name=invite.full_name,
        email=invite.email,
        expires_at=invite.expires_at,
    )


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha() -> CaptchaResponse:
    data = create_captcha()
    return CaptchaResponse(**data)


@router.post("/register/start", response_model=RegisterStartResponse)
def register_start(body: RegisterStartRequest, db: Session = Depends(get_db)) -> RegisterStartResponse:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not verify_captcha(body.captcha_id, body.captcha_answer):
        raise HTTPException(status_code=400, detail="Human verification failed — try again")

    email_l = body.email.lower()
    invite_id: Optional[int] = None
    role = "employee"
    full_name = body.full_name.strip()

    if body.invite_token:
        invite = get_valid_invite(db, body.invite_token)
        if invite is None:
            raise HTTPException(
                status_code=403,
                detail="Valid HR invite required — ask your administrator for a signup link",
            )
        if email_l != invite.email:
            raise HTTPException(status_code=400, detail="Email must match the HR invite")
        if full_name != invite.full_name.strip():
            raise HTTPException(status_code=400, detail="Full name must match the HR invite")
        invite_id = invite.id
        full_name = invite.full_name.strip()
        role = "employee"
    else:
        raise HTTPException(
            status_code=400,
            detail="Member registration uses email verification — go to /user/signup",
        )

    if db.execute(select(models.Account).where(models.Account.email == email_l)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if email_exists(email_l):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    sess = _RegisterSession(
        full_name,
        email_l,
        hash_password(body.password),
        invite_id,
        role=role,
    )
    with _lock:
        _sessions[sess.id] = sess
    return RegisterStartResponse(
        register_session_id=sess.id,
        message="Account details accepted. Proceed to palm capture.",
        verification_required=False,
    )


@router.post("/register/customer/start", response_model=RegisterStartResponse)
def register_customer_start(
    body: CustomerRegisterStartRequest,
    db: Session = Depends(get_db),
) -> RegisterStartResponse:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if not verify_captcha(body.captcha_id, body.captcha_answer):
        raise HTTPException(status_code=400, detail="Human verification failed — try again")

    try:
        account = persist_customer_account(
            db,
            email=body.email.lower(),
            password_hash=hash_password(body.password),
            username=body.username,
            email_verified=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    mail = issue_verification_code(db, account)
    return RegisterStartResponse(
        message="Verification code sent to your email. Enter it to activate your account.",
        email=account.email,
        verification_required=True,
        email_sent=bool(mail.get("sent")),
    )


@router.post("/register/customer/verify", response_model=dict)
def register_customer_verify(
    body: CustomerVerifyEmailRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        account = verify_email_code(db, email=body.email, code=body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_activity(
        db,
        account_id=account.id,
        event_type="email_verified",
        detail="customer_signup",
        commit=True,
    )
    response = _login_response(db, account, login_method="email_verify")
    response["success"] = True
    response["username"] = account.username
    response["message"] = "Email verified — signed in"
    return response


@router.post("/verify-email", response_model=dict)
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)) -> dict:
    try:
        account = verify_email_code(db, email=body.email, code=body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_activity(
        db,
        account_id=account.id,
        event_type="email_verified",
        detail=f"{account.role}_signup",
        commit=True,
    )
    response = _login_response(db, account, login_method="email_verify")
    response["success"] = True
    response["message"] = "Email verified — signed in"
    if account.username:
        response["username"] = account.username
    return response


@router.post("/resend-verification", response_model=dict)
def resend_verification(
    body: CustomerResendVerificationRequest,
    db: Session = Depends(get_db),
) -> dict:
    email_l = body.email.lower()
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="No account found for this email")
    if account.email_verified:
        raise HTTPException(status_code=400, detail="Email is already verified — sign in instead")

    mail = issue_verification_code(db, account)
    return {
        "success": True,
        "email_sent": bool(mail.get("sent")),
        "message": "Verification code resent" if mail.get("sent") else "Could not send email — check SMTP settings",
    }


@router.post("/password/forgot", response_model=dict)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    email_l = body.email.lower()
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    email_sent = False
    if account is not None:
        mail = issue_password_reset_code(db, account)
        email_sent = bool(mail.get("sent"))
    return {
        "success": True,
        "email_sent": email_sent,
        "message": (
            "If an account exists for this email, a reset code has been sent."
            if email_sent
            else "If an account exists for this email, we attempted to send a reset code. Check SMTP settings if you do not receive it."
        ),
    }


@router.post("/password/reset", response_model=dict)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        account = reset_password_with_code(
            db,
            email=body.email,
            code=body.code,
            new_password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_activity(
        db,
        account_id=account.id,
        event_type="password_reset",
        detail="email_code",
        commit=True,
    )
    return {
        "success": True,
        "role": account.role,
        "email": account.email,
        "message": "Password updated — you can sign in now",
    }


@router.post("/register/customer/resend-code", response_model=dict)
def register_customer_resend(
    body: CustomerResendVerificationRequest,
    db: Session = Depends(get_db),
) -> dict:
    return resend_verification(body, db)


@router.get("/customer/sign-in-options", response_model=CustomerSignInOptionsResponse)
def customer_sign_in_options(email: str, db: Session = Depends(get_db)) -> CustomerSignInOptionsResponse:
    email_l = email.lower().strip()
    if not email_l:
        return CustomerSignInOptionsResponse(exists=False)
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    if account is None or account.role != "customer":
        return CustomerSignInOptionsResponse(exists=False)
    return CustomerSignInOptionsResponse(
        exists=True,
        email_verified=bool(account.email_verified),
        palms_enrolled=_account_has_palms(account),
        username=account.username,
    )


@router.post("/register/palm/start", response_model=RegisterSessionStatus)
def register_palm_start(
    body: RegisterPalmStartRequest,
    db: Session = Depends(get_db),
) -> RegisterSessionStatus:
    sess = _get_reg(body.register_session_id)
    if sess.existing_account_id:
        account = db.get(models.Account, sess.existing_account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        name = account.dataset_name.strip()
        folder_id = account.dataset_id
    else:
        if not body.dataset_name:
            raise HTTPException(status_code=400, detail="Dataset name is required")
        name = body.dataset_name.strip()
        if account_exists_for_dataset(db, name):
            raise HTTPException(
                status_code=409,
                detail=f"Dataset name '{name}' is already registered",
            )
        clear_orphan_users(db, name)
        db.commit()
        folder_id = next_folder_id()
        sess.dataset_name = name
        sess.folder_id = folder_id

    sess.dataset_name = name
    sess.folder_id = folder_id
    sess.current_hand = body.first_hand
    sess.palm_started = True
    (sess.tmp_root / "Left").mkdir(parents=True, exist_ok=True)
    (sess.tmp_root / "Right").mkdir(parents=True, exist_ok=True)
    return RegisterSessionStatus(**_status(sess))


@router.post("/register/palm/capture", response_model=RegisterCaptureResponse)
def register_palm_capture(body: RegisterCaptureRequest) -> RegisterCaptureResponse:
    sess = _get_reg(body.register_session_id)
    if not sess.palm_started:
        raise HTTPException(status_code=400, detail="Start palm registration first")

    hand = sess.current_hand
    current_count = len(sess.left_embeddings if hand == "Left" else sess.right_embeddings)
    if current_count >= CAPTURES_PER_HAND:
        sess.last_error = f"{hand} hand already has {CAPTURES_PER_HAND} captures"
        return RegisterCaptureResponse(captured=False, reason=sess.last_error, **_status(sess))

    device = get_device()
    if not device.is_connected():
        sess.last_error = "Scanner not connected"
        return RegisterCaptureResponse(captured=False, reason=sess.last_error, **_status(sess))

    raw = get_fresh_frame()
    if not raw:
        sess.last_error = "No frame — hold palm 3–8 cm above the sensor"
        return RegisterCaptureResponse(captured=False, reason=sess.last_error, **_status(sess))

    idx = current_count + 1
    tmp_path = sess.tmp_root / hand / f"{idx:02d}.png"
    try:
        save_frame_png(raw, tmp_path)
        emb = embed_image(tmp_path)
    except Exception as e:
        sess.last_error = str(e)
        return RegisterCaptureResponse(captured=False, reason=sess.last_error, **_status(sess))

    if hand == "Left":
        sess.left_embeddings.append(emb)
        sess.left_paths.append(tmp_path)
    else:
        sess.right_embeddings.append(emb)
        sess.right_paths.append(tmp_path)
    sess.last_error = None
    emb_norm = float(np.linalg.norm(emb))
    logger.info(
        "Register capture ok: session=%s hand=%s idx=%d/%d norm=%.4f path=%s",
        sess.id, hand, idx, CAPTURES_PER_HAND, emb_norm, tmp_path,
    )
    return RegisterCaptureResponse(
        captured=True,
        last_capture_index=idx,
        last_capture_hand=hand,
        last_image_url=(
            f"/api/auth/register/palm/image"
            f"?register_session_id={sess.id}&hand={hand}&index={idx}"
        ),
        embedding_norm=emb_norm,
        message=f"Saved {hand} #{idx:02d} · 512-d embedding computed (norm {emb_norm:.3f})",
        **_status(sess),
    )


@router.get("/register/palm/image")
def register_palm_image(
    register_session_id: str = Query(...),
    hand: Literal["Left", "Right"] = Query(...),
    index: int = Query(..., ge=1, le=CAPTURES_PER_HAND),
) -> FileResponse:
    """Return a saved registration capture PNG for live preview in the signup UI."""
    sess = _get_reg(register_session_id)
    path = sess.tmp_root / hand / f"{index:02d}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Capture image not found")
    return FileResponse(path, media_type="image/png")


@router.post("/register/palm/switch-hand", response_model=RegisterSessionStatus)
def register_switch_hand(body: RegisterSwitchHandRequest) -> RegisterSessionStatus:
    sess = _get_reg(body.register_session_id)
    if body.next_hand == "Left" and not sess.right_complete and sess.current_hand == "Right":
        pass
    if body.next_hand == sess.current_hand:
        raise HTTPException(status_code=400, detail=f"Already capturing {body.next_hand} hand")

    done = sess.left_complete if sess.current_hand == "Left" else sess.right_complete
    if not done:
        raise HTTPException(
            status_code=400,
            detail=f"Complete {CAPTURES_PER_HAND} captures for {sess.current_hand} hand first",
        )
    sess.current_hand = body.next_hand
    sess.last_error = None
    return RegisterSessionStatus(**_status(sess))


@router.post("/register/complete", response_model=RegisterCompleteResponse)
def register_complete(
    body: RegisterCaptureRequest,
    db: Session = Depends(get_db),
) -> RegisterCompleteResponse:
    sess = _get_reg(body.register_session_id)
    if not sess.both_complete:
        raise HTTPException(
            status_code=400,
            detail=f"Need {CAPTURES_PER_HAND} captures per hand before completing",
        )

    try:
        if sess.existing_account_id:
            account = db.get(models.Account, sess.existing_account_id)
            if account is None:
                raise HTTPException(status_code=404, detail="Account not found")
            account = complete_account_palm_enrollment(
                db,
                account,
                left_embeddings=sess.left_embeddings,
                right_embeddings=sess.right_embeddings,
                left_paths=sess.left_paths,
                right_paths=sess.right_paths,
            )
            token = create_access_token(account.id, account.email)
        else:
            account, token = persist_registration(
                db,
                email=sess.email,
                password_hash=sess.password_hash,
                full_name=sess.full_name,
                dataset_name=sess.dataset_name,
                folder_id=sess.folder_id,
                left_embeddings=sess.left_embeddings,
                right_embeddings=sess.right_embeddings,
                left_paths=sess.left_paths,
                right_paths=sess.right_paths,
                copy_to_dataset=True,
                role=sess.role,
                google_sub=sess.google_sub,
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if sess.existing_account_id:
        log_activity(
            db,
            account_id=account.id,
            event_type="enrollment_complete",
            detail="customer_palm_enrollment",
            commit=True,
        )
    elif sess.invite_id is not None:
        invite = db.get(models.EmployeeInvite, sess.invite_id)
        if invite:
            mark_invite_used(db, invite, account.id)
            db.commit()
    elif account.role == "customer" and not sess.existing_account_id:
        log_activity(
            db,
            account_id=account.id,
            event_type="enrollment_complete",
            detail="customer_self_registration",
            commit=True,
        )

    shutil.rmtree(sess.tmp_root, ignore_errors=True)
    with _lock:
        _sessions.pop(sess.id, None)

    needs_email_verify = (
        not sess.existing_account_id
        and account.role == "employee"
        and not account.email_verified
    )
    if needs_email_verify:
        mail = issue_verification_code(db, account)
        return RegisterCompleteResponse(
            success=True,
            account_id=account.id,
            email=account.email,
            full_name=account.full_name,
            dataset_id=account.dataset_id,
            dataset_name=account.dataset_name,
            role=account.role,
            verification_required=True,
            email_sent=bool(mail.get("sent")),
        )

    login_method = "enrollment" if sess.existing_account_id else "signup"
    auth_sess = start_session(db, account_id=account.id, login_method=login_method)

    return RegisterCompleteResponse(
        success=True,
        account_id=account.id,
        email=account.email,
        full_name=account.full_name,
        dataset_id=account.dataset_id,
        dataset_name=account.dataset_name,
        access_token=create_access_token(account.id, account.email),
        role=account.role,
        session_id=auth_sess.id,
    )


def _customer_portal_denied(role: str) -> None:
    if role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin accounts must use the admin portal at /login",
        )
    if role == "employee":
        raise HTTPException(
            status_code=403,
            detail="Employee accounts must use the employee portal at /employee/login",
        )


def _account_has_palms(account: models.Account) -> bool:
    return bool(account.left_template and account.right_template)


def _customer_auth_response(db: Session, account: models.Account, login_method: str) -> GoogleAuthResponse:
    token = create_access_token(account.id, account.email)
    auth_sess = start_session(db, account_id=account.id, login_method=login_method)
    return GoogleAuthResponse(
        status="authenticated",
        access_token=token,
        account_id=account.id,
        email=account.email,
        full_name=account.full_name,
        dataset_id=account.dataset_id,
        dataset_name=account.dataset_name,
        role=account.role,
        session_id=auth_sess.id,
        message="Signed in successfully",
    )


def _google_register_session(full_name: str, email: str, google_sub: str) -> _RegisterSession:
    sess = _RegisterSession(
        full_name,
        email,
        hash_password(secrets.token_urlsafe(48)),
        invite_id=None,
        role="customer",
        google_sub=google_sub,
    )
    with _lock:
        _sessions[sess.id] = sess
    return sess


def _link_google_account(db: Session, account: models.Account, google_sub: str) -> models.Account:
    """Attach Google identity; Google attests email so skip our 6-digit verification."""
    if account.google_sub is not None and account.google_sub != google_sub:
        raise HTTPException(
            status_code=409,
            detail="This email is linked to a different Google account",
        )
    changed = False
    if account.google_sub is None:
        account.google_sub = google_sub
        changed = True
    if not account.email_verified:
        account.email_verified = True
        changed = True
    if changed:
        db.commit()
        db.refresh(account)
    return account


@router.get("/google/config", response_model=GoogleConfigResponse)
def google_config() -> GoogleConfigResponse:
    return GoogleConfigResponse(enabled=bool(GOOGLE_CLIENT_ID), client_id=GOOGLE_CLIENT_ID or None)


@router.post("/google", response_model=GoogleAuthResponse)
def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)) -> GoogleAuthResponse:
    profile = verify_google_credential(body.credential)
    email = profile["email"]
    google_sub = profile["sub"]
    full_name = profile["full_name"]

    account = db.execute(
        select(models.Account).where(
            (models.Account.google_sub == google_sub) | (models.Account.email == email)
        )
    ).scalar_one_or_none()

    if account is not None:
        if account.role != "customer":
            _customer_portal_denied(account.role)
        account = _link_google_account(db, account, google_sub)
        if body.intent == "signup":
            log_activity(
                db,
                account_id=account.id,
                event_type="signup_complete",
                detail="google_signup_existing",
                commit=True,
            )
        return _customer_auth_response(
            db,
            account,
            login_method="google_signup" if body.intent == "signup" else "google",
        )

    if body.intent == "login":
        raise HTTPException(status_code=404, detail="No member account found — please sign up first")

    base_username = re.sub(r"[^a-z0-9_]", "_", email.split("@")[0].lower())[:32]
    if len(base_username) < 3:
        base_username = f"user_{secrets.token_hex(3)}"
    username = base_username
    suffix = 1
    while username_taken(db, username):
        username = f"{base_username[:28]}_{suffix}"
        suffix += 1

    try:
        persist_customer_account(
            db,
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            username=username,
            full_name=full_name,
            email_verified=True,
            google_sub=google_sub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    account = db.execute(
        select(models.Account).where(models.Account.email == email)
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=500, detail="Could not create Google account")

    log_activity(
        db,
        account_id=account.id,
        event_type="signup_complete",
        detail="google_signup",
        commit=True,
    )
    return _customer_auth_response(db, account, login_method="google_signup")


@router.post("/register/enroll/start", response_model=RegisterSessionStatus)
def register_enroll_start(
    body: RegisterEnrollStartRequest,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_customer),
) -> RegisterSessionStatus:
    if _account_has_palms(account):
        raise HTTPException(status_code=400, detail="Both palms are already enrolled")
    sess = _RegisterSession(
        account.full_name,
        account.email,
        account.password_hash,
        invite_id=None,
        role="customer",
        existing_account_id=account.id,
    )
    sess.dataset_name = account.dataset_name
    sess.folder_id = account.dataset_id
    sess.current_hand = body.first_hand
    sess.palm_started = True
    (sess.tmp_root / "Left").mkdir(parents=True, exist_ok=True)
    (sess.tmp_root / "Right").mkdir(parents=True, exist_ok=True)
    with _lock:
        _sessions[sess.id] = sess
    return RegisterSessionStatus(**_status(sess))


@router.post("/login/customer/palm", response_model=PalmLoginResponse)
def login_customer_palm(db: Session = Depends(get_db)) -> PalmLoginResponse:
    t0 = time.perf_counter()
    device = get_device()
    if not device.is_connected():
        raise HTTPException(status_code=503, detail="Scanner not connected")

    try:
        probe, probe_url = _embed_live_probe("login")
    except Exception as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            latency_ms=latency_ms,
            message=str(exc),
        )

    if probe is None:
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            message="No palm detected — hold hand 3–8 cm above the sensor",
        )

    match = secure_match_probe(probe, db)
    best_account = resolve_account(db, match.account_id) if match.account_id is not None else None
    latency_ms = int((time.perf_counter() - t0) * 1000)

    if (
        not match.matched
        or best_account is None
        or best_account.role != "customer"
        or not best_account.email_verified
        or not _account_has_palms(best_account)
    ):
        msg = match.reason or "Palm not recognised — enroll your palm first or use email login"
        if best_account and best_account.role != "customer":
            msg = "This palm is not registered for the member portal"
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=float(max(0.0, match.similarity)),
            threshold=match.threshold,
            latency_ms=latency_ms,
            probe_image_url=probe_url,
            message=msg,
        )

    token = create_access_token(best_account.id, best_account.email)
    auth_sess = start_session(db, account_id=best_account.id, login_method="palm")
    return PalmLoginResponse(
        success=True,
        matched=True,
        similarity=float(match.similarity),
        threshold=match.threshold,
        access_token=token,
        account_id=best_account.id,
        email=best_account.email,
        full_name=best_account.full_name,
        dataset_id=best_account.dataset_id,
        dataset_name=best_account.dataset_name,
        hand=match.hand,
        latency_ms=latency_ms,
        probe_image_url=probe_url,
        role=best_account.role,
        session_id=auth_sess.id,
    )


@router.post("/login/customer")
def login_customer(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    email_l = body.email.lower()
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if account.role != "customer":
        _customer_portal_denied(account.role)
    if not account.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified — enter the code sent to your inbox",
        )
    return _login_response(db, account, login_method="email")


@router.post("/login")
def login_password(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    email_l = body.email.lower()
    account = db.execute(
        select(models.Account).where(models.Account.email == email_l)
    ).scalar_one_or_none()
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not account.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified — enter the code sent to your inbox",
        )
    return _login_response(db, account, login_method="email")


@router.post("/logout")
def logout(
    body: LogoutRequest,
    db: Session = Depends(get_db),
    account: models.Account = Depends(get_current_account),
) -> dict:
    settings = get_settings(db)
    if (
        account.role == "employee"
        and settings.require_palm_logout
        and not body.email_fallback
    ):
        raise HTTPException(
            status_code=403,
            detail="Employees must verify palm scan to sign out. Use palm logout or email fallback.",
        )
    if body.email_fallback:
        if account.role != "employee":
            end_session(db, account_id=account.id, session_id=body.session_id, logout_method="email")
            return {"success": True}
        if not body.password or not verify_password(body.password, account.password_hash):
            raise HTTPException(status_code=401, detail="Password required for email fallback logout")
        log_activity(
            db,
            account_id=account.id,
            event_type="logout_palm_failed",
            detail="email_fallback_used",
            commit=True,
        )
        end_session(
            db,
            account_id=account.id,
            session_id=body.session_id,
            logout_method="email_fallback",
        )
        return {"success": True}

    logout_method = "admin" if account.role == "admin" else "email"
    end_session(db, account_id=account.id, session_id=body.session_id, logout_method=logout_method)
    return {"success": True}


@router.post("/logout/palm", response_model=PalmLogoutResponse)
def logout_palm(
    body: LogoutRequest,
    db: Session = Depends(get_db),
    account: models.Account = Depends(get_current_account),
) -> PalmLogoutResponse:
    t0 = time.perf_counter()
    device = get_device()
    if not device.is_connected():
        return PalmLogoutResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            message="Scanner not connected — use Reconnect or email fallback",
        )

    raw = get_fresh_frame()
    if not raw:
        return PalmLogoutResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            message="No palm detected — hold hand above the sensor",
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    probe_path = USERS_REF_DIR / "_captures" / f"logout_{ts}.png"
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    save_frame_png(raw, probe_path)
    probe = embed_png_bytes(raw)
    probe_url = f"/api/auth/login/probe?file={probe_path.name}"

    match = secure_match_for_account(probe, account.id)
    matched = match.matched
    best_hand = match.hand
    best_sim = match.similarity

    if not matched:
        log_activity(
            db,
            account_id=account.id,
            event_type="logout_palm_failed",
            detail=f"similarity={best_sim:.4f}",
            commit=True,
        )
        return PalmLogoutResponse(
            success=False,
            matched=False,
            similarity=float(max(0.0, best_sim)),
            threshold=match.threshold,
            probe_image_url=probe_url,
            message=match.reason or f"Palm did not match — similarity {best_sim:.3f}",
        )

    end_session(db, account_id=account.id, session_id=body.session_id, logout_method="palm")
    logger.info("Palm logout ok account=%s hand=%s sim=%.4f", account.id, best_hand, best_sim)
    return PalmLogoutResponse(
        success=True,
        matched=True,
        similarity=float(best_sim),
        threshold=LOGIN_MATCH_THRESHOLD,
        probe_image_url=probe_url,
        message="Signed out successfully",
    )


@router.post("/login/palm", response_model=PalmLoginResponse)
def login_palm(db: Session = Depends(get_db)) -> PalmLoginResponse:
    t0 = time.perf_counter()
    device = get_device()
    if not device.is_connected():
        raise HTTPException(status_code=503, detail="Scanner not connected")

    try:
        probe, probe_url = _embed_live_probe("login")
    except Exception as exc:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            latency_ms=latency_ms,
            message=str(exc),
        )

    if probe is None:
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            message="No palm detected — hold hand 3–8 cm above the sensor",
        )

    match = secure_match_probe(probe, db)
    best_account = resolve_account(db, match.account_id) if match.account_id is not None else None
    latency_ms = int((time.perf_counter() - t0) * 1000)

    if not match.matched or best_account is None:
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=float(max(0.0, match.similarity)),
            threshold=match.threshold,
            latency_ms=latency_ms,
            probe_image_url=probe_url,
            message=match.reason or "Palm not recognised — try again or use email login",
        )

    if best_account.role == "admin":
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=float(match.similarity),
            threshold=match.threshold,
            latency_ms=latency_ms,
            probe_image_url=probe_url,
            message=(
                "Admin accounts must sign in with email and password. "
                "Palm-only login is disabled for admin security."
            ),
        )

    if not best_account.email_verified:
        return PalmLoginResponse(
            success=False,
            matched=False,
            similarity=float(match.similarity),
            threshold=match.threshold,
            latency_ms=latency_ms,
            probe_image_url=probe_url,
            message="Email not verified — check your inbox for the verification code",
        )

    token = create_access_token(best_account.id, best_account.email)
    auth_sess = start_session(db, account_id=best_account.id, login_method="palm")
    logger.info(
        "Palm login ok account=%s role=%s sim=%.4f margin=%.4f thr=%.4f",
        best_account.id,
        best_account.role,
        match.similarity,
        match.margin,
        match.threshold,
    )
    return PalmLoginResponse(
        success=True,
        matched=True,
        similarity=float(match.similarity),
        threshold=match.threshold,
        access_token=token,
        account_id=best_account.id,
        email=best_account.email,
        full_name=best_account.full_name,
        dataset_id=best_account.dataset_id,
        dataset_name=best_account.dataset_name,
        hand=match.hand,
        latency_ms=latency_ms,
        probe_image_url=probe_url,
        role=best_account.role,
        session_id=auth_sess.id,
    )


@router.get("/login/probe")
def login_probe_image(
    file: str = Query(..., pattern=r"^(login|logout)_[\w]+\.png$"),
) -> FileResponse:
    """Serve the PNG saved during a palm-login capture attempt."""
    path = (USERS_REF_DIR / "_captures" / file).resolve()
    root = (USERS_REF_DIR / "_captures").resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Probe image not found")
    return FileResponse(path, media_type="image/png")


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    account: models.Account = Depends(get_current_account),
) -> dict:
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    if not verify_password(body.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    account.password_hash = hash_password(body.new_password)
    log_activity(
        db,
        account_id=account.id,
        event_type="password_changed",
        detail="self_service",
    )
    db.commit()
    return {"success": True}


@router.get("/me", response_model=AuthUserResponse)
def me(account: models.Account = Depends(get_current_account)) -> AuthUserResponse:
    return AuthUserResponse(
        account_id=account.id,
        email=account.email,
        full_name=account.full_name,
        dataset_id=account.dataset_id,
        dataset_name=account.dataset_name,
        role=account.role,
    )
