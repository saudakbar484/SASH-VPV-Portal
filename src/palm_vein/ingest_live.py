"""Ingest live enrollment captures into data/raw/img for training."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from palm_vein.config import DATA_RAW, DATA_PROCESSED, PROJECT_ROOT

DATASET_DIR = PROJECT_ROOT / "data" / "dataset"
USERS_REF_DIR = PROJECT_ROOT / "data" / "users"
DB_PATH = PROJECT_ROOT / "data" / "store" / "app.db"
LIVE_SESSION = "S3"


@dataclass
class IngestReport:
    added: int = 0
    skipped_duplicate: int = 0
    skipped_existing: int = 0
    errors: list[str] = field(default_factory=list)
    sources: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "skipped_duplicate": self.skipped_duplicate,
            "skipped_existing": self.skipped_existing,
            "errors": self.errors,
            "sources": self.sources,
        }


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _ingested_sources(conn: sqlite3.Connection) -> set[str]:
    try:
        rows = conn.execute("SELECT source_path FROM training_ingest_log").fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        return set()


def _next_index(subject_dir: Path, hand: str, session: str) -> int:
    hand_code = "L" if hand == "Left" else "R"
    hand_dir = subject_dir / hand
    if not hand_dir.is_dir():
        return 1
    max_idx = 0
    for p in hand_dir.glob("*.png"):
        parts = p.stem.split("_")
        if len(parts) >= 4 and parts[0].upper() == session and parts[2].upper() == hand_code:
            try:
                max_idx = max(max_idx, int(parts[3]))
            except ValueError:
                pass
    return max_idx + 1


def _copy_image(
    src: Path,
    subject_id: str,
    hand: str,
    source_label: str,
    report: IngestReport,
    conn: sqlite3.Connection,
    ingested: set[str],
) -> None:
    src_key = str(src.resolve())
    if src_key in ingested:
        report.skipped_duplicate += 1
        return

    hand_norm = hand.capitalize()
    if hand_norm not in ("Left", "Right"):
        report.errors.append(f"Invalid hand folder: {src}")
        return

    subject_dir = DATA_RAW / subject_id.zfill(3) if subject_id.isdigit() else DATA_RAW / subject_id
    subject_dir.mkdir(parents=True, exist_ok=True)
    hand_dir = subject_dir / hand_norm
    hand_dir.mkdir(parents=True, exist_ok=True)

    hand_code = "L" if hand_norm == "Left" else "R"
    idx = _next_index(subject_dir, hand_norm, LIVE_SESSION)
    dest_name = f"{LIVE_SESSION}_{subject_id.zfill(3) if subject_id.isdigit() else subject_id}_{hand_code}_{idx}.png"
    dest = hand_dir / dest_name

    if dest.exists():
        report.skipped_existing += 1
        return

    shutil.copy2(src, dest)
    file_hash = _file_hash(src)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO training_ingest_log (source_path, dest_path, subject_id, hand, source, file_hash, ingested_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (src_key, str(dest.relative_to(PROJECT_ROOT)), subject_id.zfill(3) if subject_id.isdigit() else subject_id, hand_norm, source_label, file_hash, now),
    )
    ingested.add(src_key)
    report.added += 1
    report.sources[source_label] = report.sources.get(source_label, 0) + 1


def _scan_dataset(report: IngestReport, conn: sqlite3.Connection, ingested: set[str]) -> None:
    if not DATASET_DIR.is_dir():
        return
    for folder in sorted(DATASET_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        subject_id = folder.name.zfill(3) if folder.name.isdigit() else folder.name
        for hand_dir in folder.iterdir():
            if not hand_dir.is_dir():
                continue
            for img in sorted(hand_dir.glob("*.png")):
                _copy_image(img, subject_id, hand_dir.name, "member_enroll", report, conn, ingested)


def _scan_users_ref(report: IngestReport, conn: sqlite3.Connection, ingested: set[str]) -> None:
    if not USERS_REF_DIR.is_dir():
        return
    for user_dir in sorted(USERS_REF_DIR.iterdir()):
        if not user_dir.is_dir() or user_dir.name.startswith("_"):
            continue
        if not user_dir.name.isdigit():
            continue
        subject_id = user_dir.name.zfill(3)
        for hand_dir in user_dir.iterdir():
            if not hand_dir.is_dir():
                continue
            for img in sorted(hand_dir.glob("*.png")):
                _copy_image(img, subject_id, hand_dir.name, "admin_enroll", report, conn, ingested)


def _scan_enrollment_samples(report: IngestReport, conn: sqlite3.Connection, ingested: set[str]) -> None:
    try:
        rows = conn.execute(
            "SELECT image_path, user_id FROM enrollment_samples"
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for image_path, user_id in rows:
        src = Path(image_path)
        if not src.is_file():
            continue
        user_row = conn.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        hand_guess = "Left" if "Left" in str(src) or "\\Left\\" in str(src) or "/Left/" in str(src) else "Right"
        if user_row:
            folder_rows = conn.execute(
                "SELECT dataset_id FROM accounts WHERE dataset_name = ? LIMIT 1",
                (user_row[0],),
            ).fetchone()
            subject_id = folder_rows[0] if folder_rows and folder_rows[0] else str(user_id).zfill(3)
        else:
            subject_id = str(user_id).zfill(3)
        label = "admin_enroll" if "admin" in str(src).lower() else "enrollment_sample"
        _copy_image(src, subject_id, hand_guess, label, report, conn, ingested)


def rebuild_metadata() -> None:
    import subprocess
    import sys

    scripts = [
        PROJECT_ROOT / "scripts" / "build_metadata.py",
        PROJECT_ROOT / "scripts" / "tag_visibility.py",
        PROJECT_ROOT / "scripts" / "split_folds.py",
    ]
    for script in scripts:
        if script.is_file():
            subprocess.run([sys.executable, str(script)], cwd=str(PROJECT_ROOT), check=True)


def ingest_live_captures(*, rebuild: bool = True) -> IngestReport:
    report = IngestReport()
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        ingested = _ingested_sources(conn)
        _scan_dataset(report, conn, ingested)
        _scan_users_ref(report, conn, ingested)
        _scan_enrollment_samples(report, conn, ingested)
        conn.commit()
    finally:
        conn.close()

    if rebuild and report.added > 0:
        try:
            rebuild_metadata()
        except Exception as e:
            report.errors.append(f"metadata rebuild failed: {e}")

    report_path = DATA_PROCESSED / f"ingest_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report


def count_pending_sources() -> dict[str, int]:
    """Count enrollment PNGs not yet recorded in training_ingest_log."""
    pending: dict[str, int] = {"member_enroll": 0, "admin_enroll": 0, "total": 0}
    conn = sqlite3.connect(DB_PATH)
    try:
        ingested = _ingested_sources(conn)
    finally:
        conn.close()

    if DATASET_DIR.is_dir():
        for folder in DATASET_DIR.iterdir():
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            for hand_dir in folder.iterdir():
                if hand_dir.is_dir():
                    for img in hand_dir.glob("*.png"):
                        if str(img.resolve()) not in ingested:
                            pending["member_enroll"] += 1
                            pending["total"] += 1

    if USERS_REF_DIR.is_dir():
        for user_dir in USERS_REF_DIR.iterdir():
            if not user_dir.is_dir() or user_dir.name.startswith("_"):
                continue
            for hand_dir in user_dir.iterdir():
                if hand_dir.is_dir():
                    for img in hand_dir.glob("*.png"):
                        if str(img.resolve()) not in ingested:
                            pending["admin_enroll"] += 1
                            pending["total"] += 1
    return pending
