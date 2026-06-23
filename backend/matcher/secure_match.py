"""Secure 1:N matching with role-aware thresholds and top-1/top-2 margin."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.settings import (
    ADMIN_MATCH_THRESHOLD,
    DEFAULT_THRESHOLD,
    LOGIN_MATCH_MIN_MARGIN,
    LOGIN_MATCH_THRESHOLD,
)


@dataclass(frozen=True)
class SecureMatchResult:
    matched: bool
    account_id: Optional[int]
    email: Optional[str]
    hand: Optional[str]
    similarity: float
    second_best_similarity: float
    margin: float
    threshold: float
    reason: Optional[str] = None


def threshold_for_role(role: Optional[str]) -> float:
    if role == "admin":
        return ADMIN_MATCH_THRESHOLD
    return LOGIN_MATCH_THRESHOLD


def evaluate_probe_match(
    probe: np.ndarray,
    templates: list[tuple[int, str, str, np.ndarray]],
    *,
    role_filter: Optional[str] = None,
    threshold: Optional[float] = None,
    min_margin: Optional[float] = None,
) -> SecureMatchResult:
    """Match probe against account templates with margin check.

    templates: list of (account_id, email, hand, unit_embedding)
    """
    thr = threshold if threshold is not None else LOGIN_MATCH_THRESHOLD
    margin_req = min_margin if min_margin is not None else LOGIN_MATCH_MIN_MARGIN

    if not templates:
        return SecureMatchResult(
            matched=False,
            account_id=None,
            email=None,
            hand=None,
            similarity=-1.0,
            second_best_similarity=-1.0,
            margin=0.0,
            threshold=thr,
            reason="No palm templates enrolled",
        )

    scored: list[tuple[float, int, str, str]] = []
    for account_id, email, hand, emb in templates:
        sim = float(np.dot(probe.reshape(-1), emb.reshape(-1)))
        scored.append((sim, account_id, email, hand))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_sim, best_id, best_email, best_hand = scored[0]
    second_sim = scored[1][0] if len(scored) > 1 else -1.0
    margin = best_sim - second_sim if second_sim >= 0 else best_sim

    # Resolve role-specific threshold when we know the best candidate
    effective_thr = thr
    if role_filter is None and best_id is not None:
        # caller may pass account role via separate lookup; keep base thr here
        pass

    if best_sim < effective_thr:
        return SecureMatchResult(
            matched=False,
            account_id=best_id,
            email=best_email,
            hand=best_hand,
            similarity=best_sim,
            second_best_similarity=second_sim,
            margin=margin,
            threshold=effective_thr,
            reason=f"Similarity {best_sim:.3f} below threshold {effective_thr:.3f}",
        )

    if margin < margin_req:
        return SecureMatchResult(
            matched=False,
            account_id=best_id,
            email=best_email,
            hand=best_hand,
            similarity=best_sim,
            second_best_similarity=second_sim,
            margin=margin,
            threshold=effective_thr,
            reason=(
                f"Ambiguous match — margin {margin:.3f} below required {margin_req:.3f} "
                f"(best {best_sim:.3f}, second {second_sim:.3f})"
            ),
        )

    return SecureMatchResult(
        matched=True,
        account_id=best_id,
        email=best_email,
        hand=best_hand,
        similarity=best_sim,
        second_best_similarity=second_sim,
        margin=margin,
        threshold=effective_thr,
    )


def evaluate_gallery_match(
    probe: np.ndarray,
    similarities: np.ndarray,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    min_margin: float = LOGIN_MATCH_MIN_MARGIN,
) -> tuple[bool, float, float, float, Optional[str]]:
    """Return (matched, best_sim, second_sim, margin, reason) for User gallery rows."""
    if similarities.size == 0:
        return False, -1.0, -1.0, 0.0, "Empty gallery"

    order = np.argsort(-similarities)
    best_sim = float(similarities[order[0]])
    second_sim = float(similarities[order[1]]) if len(order) > 1 else -1.0
    margin = best_sim - second_sim if second_sim >= 0 else best_sim

    if best_sim < threshold:
        return False, best_sim, second_sim, margin, f"Below threshold {threshold:.3f}"

    if margin < min_margin:
        return (
            False,
            best_sim,
            second_sim,
            margin,
            f"Ambiguous — margin {margin:.3f} < {min_margin:.3f}",
        )

    return True, best_sim, second_sim, margin, None
