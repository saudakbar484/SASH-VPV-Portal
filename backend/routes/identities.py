"""/api/identities and /api/dataset/lookup."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import models
from backend.db.schemas import (
    DatasetClass,
    DatasetLookupResponse,
    EnrollmentSampleSummary,
    IdentitiesListResponse,
    IdentityDeleteResponse,
    IdentityDetail,
    IdentitySummary,
)
from backend.deps import get_db
from backend.matcher.dataset import load_dataset_classes, search_dataset_classes
from backend.settings import EMBEDDING_DIM, USERS_REF_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["identities"])


def _summarise(
    user: models.User,
    sample_count: int,
    accounts_by_name: dict[str, models.Account],
) -> IdentitySummary:
    account = accounts_by_name.get(user.name.strip().lower())
    if account:
        return IdentitySummary(
            id=user.id,
            name=user.name,
            hand=user.hand,
            sample_count=sample_count,
            template_dim=EMBEDDING_DIM,
            created_at=user.created_at,
            account_id=account.id,
            account_email=account.email,
            dataset_id=account.dataset_id,
            enrollment_source="registered",
        )
    return IdentitySummary(
        id=user.id,
        name=user.name,
        hand=user.hand,
        sample_count=sample_count,
        template_dim=EMBEDDING_DIM,
        created_at=user.created_at,
        enrollment_source="admin",
    )


@router.get("/identities", response_model=IdentitiesListResponse)
def list_identities(db: Session = Depends(get_db)) -> IdentitiesListResponse:
    accounts_by_name = {
        acc.dataset_name.strip().lower(): acc
        for acc in db.execute(select(models.Account)).scalars().all()
    }
    counts_sub = (
        select(
            models.EnrollmentSample.user_id,
            func.count(models.EnrollmentSample.id).label("n"),
        )
        .group_by(models.EnrollmentSample.user_id)
        .subquery()
    )
    rows = db.execute(
        select(models.User, func.coalesce(counts_sub.c.n, 0))
        .outerjoin(counts_sub, counts_sub.c.user_id == models.User.id)
        .order_by(models.User.created_at.desc())
    ).all()
    items = [_summarise(u, int(n), accounts_by_name) for u, n in rows]
    return IdentitiesListResponse(count=len(items), identities=items)


@router.get("/identities/{user_id}", response_model=IdentityDetail)
def get_identity(user_id: int, db: Session = Depends(get_db)) -> IdentityDetail:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    samples = [
        EnrollmentSampleSummary.model_validate(s)
        for s in sorted(user.samples, key=lambda s: s.captured_at)
    ]
    return IdentityDetail(
        id=user.id,
        name=user.name,
        hand=user.hand,
        sample_count=len(samples),
        template_dim=EMBEDDING_DIM,
        created_at=user.created_at,
        samples=samples,
    )


@router.delete("/identities/{user_id}", response_model=IdentityDeleteResponse)
def delete_identity(user_id: int, db: Session = Depends(get_db)) -> IdentityDeleteResponse:
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    sample_count = len(user.samples)

    user_dir = USERS_REF_DIR / str(user_id)
    deleted_images = 0
    if user_dir.exists():
        deleted_images = sum(1 for _ in user_dir.rglob("*") if _.is_file())
        shutil.rmtree(user_dir, ignore_errors=True)

    db.delete(user)
    db.commit()

    logger.info(
        "Deleted user id=%s name=%s samples=%s images=%s",
        user_id, user.name, sample_count, deleted_images,
    )

    return IdentityDeleteResponse(
        success=True,
        deleted_id=user_id,
        deleted_samples=sample_count,
        deleted_images=deleted_images,
    )


@router.get("/dataset/lookup", response_model=DatasetLookupResponse)
def dataset_lookup(
    q: str | None = Query(None, description="Optional substring of class_id"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> DatasetLookupResponse:
    total = len(load_dataset_classes())
    matches, page = search_dataset_classes(q, limit, offset)
    return DatasetLookupResponse(
        total=total,
        matches=matches,
        limit=limit,
        offset=offset,
        results=[DatasetClass(**e) for e in page],
    )
