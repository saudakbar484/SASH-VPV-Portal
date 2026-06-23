"""Load Google OAuth web client credentials from JSON or environment."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_json_path(project_root: Path, explicit: str) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = project_root / path
        return path if path.is_file() else None

    folder = project_root / "Google OAuth"
    if not folder.is_dir():
        return None

    matches = sorted(folder.glob("client_secret*.json"))
    return matches[0] if matches else None


def load_google_oauth_config(project_root: Path, json_path: str = "") -> dict[str, Any]:
    """Return web OAuth fields: client_id, client_secret, redirect_uris, etc."""
    path = _resolve_json_path(project_root, json_path.strip())
    if path is None:
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read Google OAuth JSON at %s: %s", path, exc)
        return {}

    block = raw.get("web") or raw.get("installed") or {}
    if not block.get("client_id"):
        logger.warning("Google OAuth JSON at %s has no client_id", path)
        return {}

    logger.info("Loaded Google OAuth client_id from %s", path.name)
    return block
