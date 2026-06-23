"""Lazy loader for the 244 trained dataset classes (read from production checkpoint)."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from backend.settings import CHECKPOINT_PRODUCTION

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_dataset_classes() -> list[dict[str, Any]]:
    """Return all class entries from the production checkpoint's class_to_idx.

    Result is cached; first call loads torch + the .pt file (~1-3 s).
    Each entry: {class_id, user_id, hand, class_idx}.
    """
    import torch  # heavy - keep inside the function

    if not CHECKPOINT_PRODUCTION.exists():
        logger.warning("Checkpoint missing: %s", CHECKPOINT_PRODUCTION)
        return []

    logger.info("Loading dataset class_to_idx from %s ...", CHECKPOINT_PRODUCTION.name)
    ckpt = torch.load(CHECKPOINT_PRODUCTION, map_location="cpu", weights_only=False)
    class_to_idx = ckpt.get("class_to_idx", {})

    entries: list[dict[str, Any]] = []
    for key, idx in class_to_idx.items():
        if isinstance(key, tuple) and len(key) == 2:
            user_id, hand = key
        else:
            user_id, hand = str(key), ""
        entries.append(
            {
                "class_id": f"{user_id}_{hand}" if hand else str(user_id),
                "user_id": str(user_id),
                "hand": str(hand),
                "class_idx": int(idx),
            }
        )
    entries.sort(key=lambda e: (e["user_id"], e["hand"]))
    logger.info("Loaded %d trained dataset classes", len(entries))
    return entries


def search_dataset_classes(q: str | None, limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
    """Substring filter on class_id (case-insensitive). Returns (matches, page)."""
    all_entries = load_dataset_classes()
    if q:
        ql = q.lower()
        filtered = [e for e in all_entries if ql in e["class_id"].lower()]
    else:
        filtered = all_entries
    page = filtered[offset : offset + limit]
    return len(filtered), page
