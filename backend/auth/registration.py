"""Shared registration persistence helpers."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.folder_mapping import append_row, dataset_name_taken, email_exists, next_folder_id, read_rows
from backend.auth.jwt_tokens import create_access_token
from backend.auth.template_cache import refresh_account_templates
from backend.db import models
from backend.settings import DATASET_DIR, USERS_REF_DIR
from backend.utils.embeddings import average_and_normalise, embedding_to_bytes

logger = logging.getLogger(__name__)

CAPTURES_PER_HAND = 10


def account_exists_for_dataset(db: Session, dataset_name: str) -> bool:
    name = dataset_name.strip()
    if (
        db.execute(select(models.Account).where(models.Account.dataset_name == name))
        .scalar_one_or_none()
    ):
        return True
    return dataset_name_taken(name)


def folder_id_taken(db: Session, folder_id: str) -> bool:
    fid = folder_id.strip()
    if (
        db.execute(select(models.Account).where(models.Account.dataset_id == fid))
        .scalar_one_or_none()
    ):
        return True
    return any(r.get("folder_id") == fid for r in read_rows())


def clear_orphan_users(db: Session, dataset_name: str) -> int:
    """Remove legacy User rows with no linked Account (partial/failed signup)."""
    if account_exists_for_dataset(db, dataset_name):
        return 0

    users = list(
        db.execute(select(models.User).where(models.User.name == dataset_name.strip()))
        .scalars()
        .all()
    )
    for user in users:
        user_dir = USERS_REF_DIR / str(user.id)
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
        db.delete(user)
    if users:
        db.flush()
        logger.info(
            "Cleared %d orphan identity row(s) for dataset name %r",
            len(users),
            dataset_name,
        )
    return len(users)


def persist_registration(
    db: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    dataset_name: str,
    folder_id: str,
    left_embeddings: list[np.ndarray],
    right_embeddings: list[np.ndarray],
    left_paths: list[Path],
    right_paths: list[Path],
    copy_to_dataset: bool = True,
    role: str = "employee",
    google_sub: str | None = None,
) -> tuple[models.Account, str]:
    """Create Account + User rows, ref samples, dataset folder, and CSV row."""
    email_l = email.lower().strip()
    dataset_name = dataset_name.strip()
    folder_id = folder_id.strip()

    if len(left_embeddings) < CAPTURES_PER_HAND or len(right_embeddings) < CAPTURES_PER_HAND:
        raise ValueError(f"Need {CAPTURES_PER_HAND} captures per hand")

    if db.execute(select(models.Account).where(models.Account.email == email_l)).scalar_one_or_none():
        raise ValueError("An account with this email already exists")
    if email_exists(email_l):
        raise ValueError("An account with this email already exists")
    if account_exists_for_dataset(db, dataset_name):
        raise ValueError(f"Dataset name '{dataset_name}' is already registered")
    if folder_id_taken(db, folder_id):
        raise ValueError(f"Folder id '{folder_id}' is already registered")

    clear_orphan_users(db, dataset_name)

    left_tpl = average_and_normalise(left_embeddings)
    right_tpl = average_and_normalise(right_embeddings)

    account = models.Account(
        email=email_l,
        password_hash=password_hash,
        full_name=full_name.strip(),
        dataset_id=folder_id,
        dataset_name=dataset_name,
        role=role if role in ("admin", "employee", "customer") else "employee",
        left_template=embedding_to_bytes(left_tpl),
        right_template=embedding_to_bytes(right_tpl),
        google_sub=google_sub,
    )
    db.add(account)
    db.flush()

    for hand, tpl, embs, paths in (
        ("Left", left_tpl, left_embeddings, left_paths),
        ("Right", right_tpl, right_embeddings, right_paths),
    ):
        user = models.User(
            name=dataset_name,
            hand=hand,
            template_embedding=embedding_to_bytes(tpl),
        )
        db.add(user)
        db.flush()
        ref_dir = USERS_REF_DIR / str(user.id) / hand
        ref_dir.mkdir(parents=True, exist_ok=True)
        for emb, src in zip(embs, paths):
            dst = ref_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(str(src), str(dst))
            db.add(
                models.EnrollmentSample(
                    user_id=user.id,
                    image_path=str(dst),
                    embedding=embedding_to_bytes(emb),
                )
            )

    try:
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Registration failed: this dataset identity or email is already registered."
        ) from exc

    if copy_to_dataset:
        dest_root = DATASET_DIR / folder_id
        for hand, paths in (("Left", left_paths), ("Right", right_paths)):
            hand_dir = dest_root / hand
            hand_dir.mkdir(parents=True, exist_ok=True)
            for src in paths:
                dst = hand_dir / src.name
                if src.resolve() != dst.resolve():
                    shutil.copy2(str(src), str(dst))

    append_row(
        folder_id=folder_id,
        dataset_name=dataset_name,
        email=email_l,
        full_name=full_name.strip(),
        account_id=account.id,
    )

    refresh_account_templates(db)

    token = create_access_token(account.id, account.email)
    logger.info(
        "Registered account id=%s email=%s dataset_id=%s",
        account.id,
        account.email,
        account.dataset_id,
    )
    return account, token


def username_taken(db: Session, username: str) -> bool:
    uname = username.strip().lower()
    if (
        db.execute(select(models.Account).where(models.Account.username == uname))
        .scalar_one_or_none()
    ):
        return True
    return account_exists_for_dataset(db, uname)


def persist_customer_account(
    db: Session,
    *,
    email: str,
    password_hash: str,
    username: str,
    full_name: str | None = None,
    email_verified: bool = False,
    google_sub: str | None = None,
) -> models.Account:
    """Create a member account without palm templates."""
    email_l = email.lower().strip()
    uname = username.strip().lower()
    display = (full_name or username).strip()

    if db.execute(select(models.Account).where(models.Account.email == email_l)).scalar_one_or_none():
        raise ValueError("An account with this email already exists")
    if email_exists(email_l):
        raise ValueError("An account with this email already exists")
    if username_taken(db, uname):
        raise ValueError("This username is already taken")

    folder_id = next_folder_id()
    while folder_id_taken(db, folder_id):
        folder_id = next_folder_id()

    account = models.Account(
        email=email_l,
        username=uname,
        password_hash=password_hash,
        full_name=display,
        dataset_id=folder_id,
        dataset_name=display,
        role="customer",
        email_verified=email_verified,
        google_sub=google_sub,
        left_template=None,
        right_template=None,
    )
    db.add(account)
    try:
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Registration failed: email or username already exists") from exc

    append_row(
        folder_id=folder_id,
        dataset_name=display,
        email=email_l,
        full_name=display,
        account_id=account.id,
    )
    logger.info("Created customer account id=%s username=%s", account.id, uname)
    return account


def complete_account_palm_enrollment(
    db: Session,
    account: models.Account,
    *,
    left_embeddings: list[np.ndarray],
    right_embeddings: list[np.ndarray],
    left_paths: list[Path],
    right_paths: list[Path],
) -> models.Account:
    """Attach palm templates to an existing member account."""
    dataset_name = account.dataset_name.strip()
    if len(left_embeddings) < CAPTURES_PER_HAND or len(right_embeddings) < CAPTURES_PER_HAND:
        raise ValueError(f"Need {CAPTURES_PER_HAND} captures per hand")

    clear_orphan_users(db, dataset_name)

    left_tpl = average_and_normalise(left_embeddings)
    right_tpl = average_and_normalise(right_embeddings)
    account.left_template = embedding_to_bytes(left_tpl)
    account.right_template = embedding_to_bytes(right_tpl)

    for hand, tpl, embs, paths in (
        ("Left", left_tpl, left_embeddings, left_paths),
        ("Right", right_tpl, right_embeddings, right_paths),
    ):
        existing = db.execute(
            select(models.User).where(models.User.name == dataset_name, models.User.hand == hand)
        ).scalar_one_or_none()
        if existing:
            db.delete(existing)
            db.flush()

        user = models.User(
            name=dataset_name,
            hand=hand,
            template_embedding=embedding_to_bytes(tpl),
        )
        db.add(user)
        db.flush()
        ref_dir = USERS_REF_DIR / str(user.id) / hand
        ref_dir.mkdir(parents=True, exist_ok=True)
        for emb, src in zip(embs, paths):
            dst = ref_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(str(src), str(dst))
            db.add(
                models.EnrollmentSample(
                    user_id=user.id,
                    image_path=str(dst),
                    embedding=embedding_to_bytes(emb),
                )
            )

    dest_root = DATASET_DIR / account.dataset_id
    for hand, paths in (("Left", left_paths), ("Right", right_paths)):
        hand_dir = dest_root / hand
        hand_dir.mkdir(parents=True, exist_ok=True)
        for src in paths:
            dst = hand_dir / src.name
            if src.resolve() != dst.resolve():
                shutil.copy2(str(src), str(dst))

    db.commit()
    db.refresh(account)
    refresh_account_templates(db)
    return account
