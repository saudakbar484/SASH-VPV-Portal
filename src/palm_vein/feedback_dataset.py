"""Export hard-negative and positive pairs from recognition logs for training."""
from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from palm_vein.config import DATA_PROCESSED, PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "store" / "app.db"
FEEDBACK_CSV = DATA_PROCESSED / "feedback_pairs.csv"
CAPTURES_DIR = PROJECT_ROOT / "data" / "users" / "_captures"


def export_feedback_pairs(since: datetime | None = None) -> int:
    """Write probe/anchor pairs from recognition_logs and activity_logs."""
    conn = sqlite3.connect(DB_PATH)
    rows: list[dict[str, str | float]] = []

    try:
        sql = """
            SELECT mode, claimed_name, matched_name, similarity, matched, threshold, created_at
            FROM recognition_logs
        """
        params: tuple = ()
        if since:
            sql += " WHERE created_at >= ?"
            params = (since.isoformat(),)
        sql += " ORDER BY created_at DESC LIMIT 5000"
        for mode, claimed, matched, sim, matched_flag, thr, created in conn.execute(sql, params):
            if mode == "verify" and claimed and matched_flag:
                rows.append({
                    "probe_path": "",
                    "anchor_subject": claimed,
                    "label": "positive",
                    "weight": "1.0",
                    "source": "recognition_verify",
                    "similarity": str(sim),
                    "created_at": created,
                })
            elif mode == "identify" and matched_flag and matched:
                rows.append({
                    "probe_path": "",
                    "anchor_subject": matched,
                    "label": "positive",
                    "weight": "1.0",
                    "source": "recognition_identify",
                    "similarity": str(sim),
                    "created_at": created,
                })
            elif not matched_flag and sim >= float(thr) * 0.9:
                rows.append({
                    "probe_path": "",
                    "anchor_subject": matched or claimed or "",
                    "label": "hard_negative",
                    "weight": "1.5",
                    "source": "near_miss",
                    "similarity": str(sim),
                    "created_at": created,
                })

        act_sql = """
            SELECT event_type, detail, created_at FROM activity_logs
            WHERE event_type IN ('customer_palm_verify_failed', 'logout_palm_failed', 'login_failed')
        """
        if since:
            act_sql += " AND created_at >= ?"
        for event_type, detail, created in conn.execute(act_sql, params if since else ()):
            rows.append({
                "probe_path": "",
                "anchor_subject": "",
                "label": "hard_negative",
                "weight": "1.2",
                "source": event_type,
                "similarity": detail or "",
                "created_at": created,
            })
    finally:
        conn.close()

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    fieldnames = ["probe_path", "anchor_subject", "label", "weight", "source", "similarity", "created_at"]
    with open(FEEDBACK_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
