#!/usr/bin/env python3
"""Finalize a failed signup from images already saved under data/dataset/{folder_id}/."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.auth.passwords import hash_password  # noqa: E402
from backend.auth.registration import CAPTURES_PER_HAND, persist_registration  # noqa: E402
from backend.db.base import SessionLocal  # noqa: E402
from backend.matcher.singleton import embed_image  # noqa: E402
from backend.settings import DATASET_DIR  # noqa: E402


def _load_hand(folder_id: str, hand: str) -> tuple[list, list[Path]]:
    hand_dir = DATASET_DIR / folder_id / hand
    if not hand_dir.is_dir():
        raise SystemExit(f"Missing folder: {hand_dir}")
    paths = sorted(hand_dir.glob("*.png"))
    if len(paths) < CAPTURES_PER_HAND:
        raise SystemExit(
            f"{hand} hand has {len(paths)} images; need {CAPTURES_PER_HAND} in {hand_dir}"
        )
    paths = paths[:CAPTURES_PER_HAND]
    embeddings = [embed_image(p) for p in paths]
    return embeddings, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder-id", required=True, help="e.g. 001")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dataset-name", required=True)
    args = parser.parse_args()

    left_embs, left_paths = _load_hand(args.folder_id, "Left")
    right_embs, right_paths = _load_hand(args.folder_id, "Right")

    db = SessionLocal()
    try:
        account, token = persist_registration(
            db,
            email=args.email,
            password_hash=hash_password(args.password),
            full_name=args.full_name,
            dataset_name=args.dataset_name,
            folder_id=args.folder_id,
            left_embeddings=left_embs,
            right_embeddings=right_embs,
            left_paths=left_paths,
            right_paths=right_paths,
            copy_to_dataset=False,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        db.close()

    print(f"OK account_id={account.id} dataset_id={account.dataset_id}")
    print(f"access_token={token}")


if __name__ == "__main__":
    main()
