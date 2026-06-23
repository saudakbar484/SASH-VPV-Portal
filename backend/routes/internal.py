"""Internal endpoints for schedulers and ops (not for browser use)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.attendance import close_day_absences
from backend.deps import get_db
from backend.settings import ATTENDANCE_CRON_SECRET

router = APIRouter(prefix="/api/internal", tags=["internal"])


class InternalCloseDayRequest(BaseModel):
    work_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class InternalCloseDayResponse(BaseModel):
    success: bool
    work_date: str
    marked_absent: int
    half_days: int = 0
    skipped: bool = False
    reason: Optional[str] = None


def _require_cron_secret(x_cron_secret: str = Header(..., alias="X-Cron-Secret")) -> None:
    if not ATTENDANCE_CRON_SECRET:
        raise HTTPException(status_code=503, detail="ATTENDANCE_CRON_SECRET not configured")
    if x_cron_secret != ATTENDANCE_CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/attendance/close-day", response_model=InternalCloseDayResponse)
def internal_close_attendance_day(
    body: InternalCloseDayRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_cron_secret),
) -> InternalCloseDayResponse:
    """Mark absences for a work day — call from Task Scheduler / cron with X-Cron-Secret header."""
    result = close_day_absences(db, work_date=body.work_date)
    return InternalCloseDayResponse(
        success=True,
        work_date=str(result["work_date"]),
        marked_absent=int(result["marked_absent"]),
        half_days=int(result.get("half_days", 0)),
        skipped=bool(result.get("skipped", False)),
        reason=str(result.get("reason") or "") or None,
    )
