"""/api/dashboard/* — post-login dashboard aggregates."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db import models
from backend.deps import get_db
from backend.deps_auth import get_current_account
from backend.device.singleton import get_device

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    scanner_connected: bool
    scanner_message: str
    enrolled_persons: int
    dataset_classes: int
    image_resolution: str
    feature_size: int | None


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    _account: models.Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> DashboardStats:
    device = get_device()
    connected = device.is_connected()
    enrolled = db.execute(select(func.count(models.Account.id))).scalar_one()
    from backend.matcher.dataset import load_dataset_classes

    classes = len(load_dataset_classes())
    feat_size = getattr(device, "feat_size", None)
    return DashboardStats(
        scanner_connected=connected,
        scanner_message="Connected" if connected else "Offline",
        enrolled_persons=enrolled,
        dataset_classes=classes,
        image_resolution="480×640",
        feature_size=feat_size,
    )
