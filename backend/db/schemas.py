"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class IdentitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hand: str
    sample_count: int
    template_dim: int
    created_at: datetime
    account_id: Optional[int] = None
    account_email: Optional[str] = None
    dataset_id: Optional[str] = None
    enrollment_source: Literal["registered", "admin"] = "admin"


class IdentitiesListResponse(BaseModel):
    count: int
    identities: list[IdentitySummary]


class IdentityDeleteResponse(BaseModel):
    success: bool
    deleted_id: int
    deleted_samples: int
    deleted_images: int


class DatasetClass(BaseModel):
    class_id: str  # "<user>_<hand>"
    user_id: str
    hand: str
    class_idx: int


class DatasetLookupResponse(BaseModel):
    total: int
    matches: int
    limit: int
    offset: int
    results: list[DatasetClass]


class RecognitionLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    mode: Literal["verify", "identify"]
    claimed_name: Optional[str] = None
    matched_name: Optional[str] = None
    similarity: float
    matched: bool
    threshold: float
    latency_ms: int
    created_at: datetime


class EnrollmentSampleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_path: str
    captured_at: datetime


class IdentityDetail(IdentitySummary):
    samples: list[EnrollmentSampleSummary] = Field(default_factory=list)


# ---- Recognition (Phase 5) ----


class VerifyRequest(BaseModel):
    user_id: Optional[int] = Field(default=None, description="Numeric user id (legacy per-hand)")
    account_id: Optional[int] = Field(
        default=None,
        description="Registered account id — verifies against both Left and Right templates",
    )
    name: Optional[str] = Field(default=None, description="Username; used if ids are omitted")


class VerifyResponse(BaseModel):
    matched: bool
    similarity: float
    threshold: float
    confidence: float
    user_id: int
    claimed_name: str
    hand: str
    latency_ms: int
    captured_at: datetime
    log_id: int
    probe_image_path: Optional[str] = None
    rejected_reason: Optional[str] = None


class IdentifyRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20)


class IdentifyCandidate(BaseModel):
    user_id: int
    name: str
    hand: str
    similarity: float
    confidence: float


class IdentifyResponse(BaseModel):
    matched: bool
    best_match: Optional[IdentifyCandidate] = None
    candidates: list[IdentifyCandidate] = Field(default_factory=list)
    threshold: float
    gallery_size: int
    latency_ms: int
    captured_at: datetime
    log_id: int
    probe_image_path: Optional[str] = None
    rejected_reason: Optional[str] = None


class RecognitionLogsResponse(BaseModel):
    count: int
    accepted: int
    rejected: int
    limit: int
    offset: int
    logs: list[RecognitionLogEntry]
    enabled: bool = True
