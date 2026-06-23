"""Admin APIs for weekly model retraining."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.db import models
from backend.deps import get_db
from backend.routes.admin import require_admin

router = APIRouter(prefix="/api/admin/training", tags=["admin-training"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEEKLY_REPORT = PROJECT_ROOT / "data" / "processed" / "weekly_retrain_last.json"
_training_lock = threading.Lock()
_training_in_progress = False


class TrainingStatusResponse(BaseModel):
    last_trained_at: str | None
    pending_images: int
    pending_sources: dict[str, int]
    days_since_train: int
    show_reminder_banner: bool
    training_in_progress: bool
    last_run_status: str | None
    last_val_eer: float | None
    last_val_rank1: float | None
    images_ingested_last: int | None


class TrainingRunResponse(BaseModel):
    message: str
    run_id: int | None = None


def _count_pending() -> dict[str, int]:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from palm_vein.ingest_live import count_pending_sources
    return count_pending_sources()


@router.get("/status", response_model=TrainingStatusResponse)
def training_status(
    db: Session = Depends(get_db),
    _admin: models.Account = Depends(require_admin),
) -> TrainingStatusResponse:
    last_run = db.execute(
        select(models.TrainingRun).order_by(desc(models.TrainingRun.started_at)).limit(1)
    ).scalar_one_or_none()

    pending = _count_pending()
    last_trained_at: datetime | None = None
    last_status: str | None = None
    last_eer: float | None = None
    last_rank1: float | None = None
    images_ingested: int | None = None

    if last_run and last_run.status == "success":
        last_trained_at = last_run.completed_at or last_run.started_at
        last_status = last_run.status
        last_eer = last_run.val_eer
        last_rank1 = last_run.val_rank1
        images_ingested = last_run.images_ingested
    elif WEEKLY_REPORT.is_file():
        try:
            data = json.loads(WEEKLY_REPORT.read_text(encoding="utf-8"))
            if data.get("completed_at"):
                last_trained_at = datetime.fromisoformat(data["completed_at"])
            last_status = data.get("status")
            last_eer = data.get("val_eer")
            last_rank1 = data.get("val_rank1")
            images_ingested = data.get("images_ingested")
        except (json.JSONDecodeError, ValueError):
            pass

    days_since = 999
    if last_trained_at:
        if last_trained_at.tzinfo is None:
            last_trained_at = last_trained_at.replace(tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_trained_at).days

    show_banner = pending["total"] > 0 and days_since >= 7

    return TrainingStatusResponse(
        last_trained_at=last_trained_at.isoformat() if last_trained_at else None,
        pending_images=pending["total"],
        pending_sources=pending,
        days_since_train=days_since,
        show_reminder_banner=show_banner,
        training_in_progress=_training_in_progress,
        last_run_status=last_status,
        last_val_eer=last_eer,
        last_val_rank1=last_rank1,
        images_ingested_last=images_ingested,
    )


def _run_training_job(run_id: int) -> None:
    global _training_in_progress
    script = PROJECT_ROOT / "scripts" / "weekly_retrain.py"
    try:
        subprocess.run([sys.executable, str(script)], cwd=str(PROJECT_ROOT), check=True)
        status = "success"
        detail = "Weekly retrain completed"
        val_eer = None
        val_rank1 = None
        images_ingested = 0
        if WEEKLY_REPORT.is_file():
            data = json.loads(WEEKLY_REPORT.read_text(encoding="utf-8"))
            status = data.get("status", "success")
            detail = data.get("rollback_reason") or detail
            val_eer = data.get("val_eer")
            val_rank1 = data.get("val_rank1")
            images_ingested = data.get("images_ingested", 0)
    except subprocess.CalledProcessError as e:
        status = "failed"
        detail = str(e)
        val_eer = None
        val_rank1 = None
        images_ingested = 0

    from backend.db.base import SessionLocal
    from backend.matcher.singleton import reload_matcher

    db = SessionLocal()
    try:
        run = db.get(models.TrainingRun, run_id)
        if run:
            run.status = status
            run.detail = detail
            run.val_eer = val_eer
            run.val_rank1 = val_rank1
            run.images_ingested = images_ingested or 0
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

    if status == "success":
        try:
            reload_matcher()
        except Exception:
            pass

    with _training_lock:
        _training_in_progress = False


@router.post("/run", response_model=TrainingRunResponse)
def run_training(
    db: Session = Depends(get_db),
    _admin: models.Account = Depends(require_admin),
) -> TrainingRunResponse:
    global _training_in_progress
    with _training_lock:
        if _training_in_progress:
            raise HTTPException(status_code=409, detail="Training already in progress")
        _training_in_progress = True

    run = models.TrainingRun(status="running", trigger="manual")
    db.add(run)
    db.commit()
    db.refresh(run)

    thread = threading.Thread(target=_run_training_job, args=(run.id,), daemon=True)
    thread.start()
    return TrainingRunResponse(message="Training started in background", run_id=run.id)
