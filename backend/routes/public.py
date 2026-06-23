"""Public marketing and contact APIs (no auth)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.notifications import resolve_admin_notify_email, send_email_detailed
from backend.db import models
from backend.deps import get_db

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicStatsResponse(BaseModel):
    total_customers: int
    total_employees: int
    enrolled_identities: int
    match_threshold: float


class ContactRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    email: EmailStr
    organization: Optional[str] = Field(default=None, max_length=256)
    subject: str = Field(min_length=2, max_length=64)
    message: str = Field(min_length=10, max_length=4000)


class ContactResponse(BaseModel):
    success: bool
    message: str


@router.get("/stats", response_model=PublicStatsResponse)
def public_stats(db: Session = Depends(get_db)) -> PublicStatsResponse:
    customers = db.execute(
        select(func.count()).select_from(models.Account).where(models.Account.role == "customer")
    ).scalar_one()
    employees = db.execute(
        select(func.count()).select_from(models.Account).where(models.Account.role == "employee")
    ).scalar_one()
    identities = db.execute(select(func.count()).select_from(models.User)).scalar_one()
    from backend.settings import DEFAULT_THRESHOLD

    return PublicStatsResponse(
        total_customers=int(customers or 0),
        total_employees=int(employees or 0),
        enrolled_identities=int(identities or 0),
        match_threshold=DEFAULT_THRESHOLD,
    )


@router.post("/contact", response_model=ContactResponse)
def submit_contact(body: ContactRequest, db: Session = Depends(get_db)) -> ContactResponse:
    to = resolve_admin_notify_email(db)
    org_line = f"\nOrganization: {body.organization}" if body.organization else ""
    email_body = (
        f"New contact form submission\n\n"
        f"Name: {body.name}\n"
        f"Email: {body.email}"
        f"{org_line}\n"
        f"Subject: {body.subject}\n\n"
        f"Message:\n{body.message}\n"
    )
    result = send_email_detailed(
        to=to,
        subject=f"[Palm Vein] Contact: {body.subject}",
        body=email_body,
    )
    if result.get("sent"):
        return ContactResponse(success=True, message="Thank you — we will respond shortly.")
    return ContactResponse(
        success=True,
        message="Message received. Email delivery is pending — we will follow up soon.",
    )
