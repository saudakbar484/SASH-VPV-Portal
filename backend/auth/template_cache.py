"""In-memory cache of registered account palm templates for fast palm login."""

from __future__ import annotations



import logging

from threading import Lock

from typing import Optional



import numpy as np

from sqlalchemy import select

from sqlalchemy.orm import Session



from backend.db import models

from backend.matcher.secure_match import SecureMatchResult, evaluate_probe_match, threshold_for_role

from backend.settings import LOGIN_MATCH_MIN_MARGIN, LOGIN_MATCH_THRESHOLD

from backend.utils.embeddings import bytes_to_embedding



logger = logging.getLogger(__name__)



_lock = Lock()

_cached: list[tuple[int, str, str, np.ndarray]] = []





def refresh_account_templates(db: Session) -> int:

    """Load all account left/right templates into memory. Returns template count."""

    global _cached

    rows: list[tuple[int, str, str, np.ndarray]] = []

    for acc in db.execute(select(models.Account)).scalars().all():

        for hand, blob in (("Left", acc.left_template), ("Right", acc.right_template)):

            if not blob:

                continue

            rows.append((acc.id, acc.email, hand, bytes_to_embedding(blob)))

    with _lock:

        _cached = rows

    logger.info("Account template cache refreshed: %d templates", len(rows))

    return len(rows)





def secure_match_for_account(probe: np.ndarray, account_id: int) -> SecureMatchResult:
    """1:1 account verify with global margin check against all cached templates."""
    with _lock:
        templates = list(_cached)

    account_entries = [e for e in templates if e[0] == account_id]
    if not account_entries:
        return SecureMatchResult(
            matched=False,
            account_id=account_id,
            email=None,
            hand=None,
            similarity=-1.0,
            second_best_similarity=-1.0,
            margin=0.0,
            threshold=LOGIN_MATCH_THRESHOLD,
            reason="No palm templates enrolled for this account",
        )

    scored: list[tuple[float, int, str, str]] = []
    for entry in templates:
        sim = float(np.dot(probe.reshape(-1), entry[3].reshape(-1)))
        scored.append((sim, entry[0], entry[1], entry[2]))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_sim, best_id, best_email, best_hand = scored[0]
    second_sim = scored[1][0] if len(scored) > 1 else -1.0
    margin = best_sim - second_sim if second_sim >= 0 else best_sim

    account_best = max(float(np.dot(probe, e[3])) for e in account_entries)
    account_hand = next(e[2] for e in account_entries if float(np.dot(probe, e[3])) == account_best)
    account_email = account_entries[0][1]

    if best_id != account_id:
        return SecureMatchResult(
            matched=False,
            account_id=account_id,
            email=account_email,
            hand=account_hand,
            similarity=account_best,
            second_best_similarity=second_sim,
            margin=margin,
            threshold=LOGIN_MATCH_THRESHOLD,
            reason="Another account scored higher in the gallery",
        )

    if account_best < LOGIN_MATCH_THRESHOLD:
        return SecureMatchResult(
            matched=False,
            account_id=account_id,
            email=account_email,
            hand=account_hand,
            similarity=account_best,
            second_best_similarity=second_sim,
            margin=margin,
            threshold=LOGIN_MATCH_THRESHOLD,
            reason=f"Similarity {account_best:.3f} below threshold {LOGIN_MATCH_THRESHOLD:.3f}",
        )

    if margin < LOGIN_MATCH_MIN_MARGIN:
        return SecureMatchResult(
            matched=False,
            account_id=account_id,
            email=account_email,
            hand=account_hand,
            similarity=account_best,
            second_best_similarity=second_sim,
            margin=margin,
            threshold=LOGIN_MATCH_THRESHOLD,
            reason=(
                f"Ambiguous match — margin {margin:.3f} below required {LOGIN_MATCH_MIN_MARGIN:.3f}"
            ),
        )

    return SecureMatchResult(
        matched=True,
        account_id=account_id,
        email=account_email,
        hand=account_hand,
        similarity=account_best,
        second_best_similarity=second_sim,
        margin=margin,
        threshold=LOGIN_MATCH_THRESHOLD,
    )


def match_probe_for_account(probe: np.ndarray, account_id: int) -> tuple[Optional[str], float]:

    """Match probe against one account's left/right templates only."""

    with _lock:

        templates = [e for e in _cached if e[0] == account_id]

    best_sim = -1.0

    best_hand: Optional[str] = None

    for entry in templates:

        sim = float(np.dot(probe, entry[3]))

        if sim > best_sim:

            best_sim = sim

            best_hand = entry[2]

    return best_hand, best_sim





def match_probe(probe: np.ndarray) -> tuple[Optional[int], Optional[str], float]:

    """Return best matching account id, hand, and similarity from cache (legacy)."""

    with _lock:

        templates = list(_cached)

    if not templates:

        return None, None, -1.0

    best_sim = -1.0

    best: tuple[int, str, str, np.ndarray] | None = None

    for entry in templates:

        sim = float(np.dot(probe, entry[3]))

        if sim > best_sim:

            best_sim = sim

            best = entry

    if best is None:

        return None, None, -1.0

    return best[0], best[2], best_sim





def secure_match_probe(probe: np.ndarray, db: Session) -> SecureMatchResult:

    """Match with login thresholds and top-1/top-2 margin; role-aware for admin."""

    with _lock:

        templates = list(_cached)



    base = evaluate_probe_match(

        probe,

        templates,

        threshold=LOGIN_MATCH_THRESHOLD,

        min_margin=LOGIN_MATCH_MIN_MARGIN,

    )

    if not base.matched or base.account_id is None:

        return base



    account = db.get(models.Account, base.account_id)

    if account is None:

        return SecureMatchResult(

            matched=False,

            account_id=base.account_id,

            email=base.email,

            hand=base.hand,

            similarity=base.similarity,

            second_best_similarity=base.second_best_similarity,

            margin=base.margin,

            threshold=base.threshold,

            reason="Matched account not found",

        )



    role_thr = threshold_for_role(account.role)

    if base.similarity < role_thr:

        return SecureMatchResult(

            matched=False,

            account_id=base.account_id,

            email=base.email,

            hand=base.hand,

            similarity=base.similarity,

            second_best_similarity=base.second_best_similarity,

            margin=base.margin,

            threshold=role_thr,

            reason=f"Similarity {base.similarity:.3f} below {account.role} threshold {role_thr:.3f}",

        )



    return SecureMatchResult(

        matched=True,

        account_id=base.account_id,

        email=base.email,

        hand=base.hand,

        similarity=base.similarity,

        second_best_similarity=base.second_best_similarity,

        margin=base.margin,

        threshold=role_thr,

    )





def resolve_account(db: Session, account_id: int) -> Optional[models.Account]:

    return db.get(models.Account, account_id)

