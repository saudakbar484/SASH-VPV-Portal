#!/usr/bin/env python3
"""Weekly supervised retrain: ingest live captures, fine-tune, evaluate, deploy."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from palm_vein.config import CHECKPOINT_PRODUCTION, DATA_PROCESSED, METRICS_DIR  # noqa: E402
from palm_vein.feedback_dataset import export_feedback_pairs  # noqa: E402
from palm_vein.ingest_live import ingest_live_captures  # noqa: E402
from palm_vein.train import main as train_main  # noqa: E402

WEEKLY_REPORT = DATA_PROCESSED / "weekly_retrain_last.json"
EER_TOLERANCE = 0.05
RANK1_TOLERANCE = 0.05


def _load_previous_metrics() -> dict | None:
    if not WEEKLY_REPORT.is_file():
        return None
    try:
        return json.loads(WEEKLY_REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_weekly_retrain(*, epochs: int = 20, batch_size: int = 16) -> dict:
    started = datetime.now(timezone.utc)
    report: dict = {
        "started_at": started.isoformat(),
        "status": "running",
        "images_ingested": 0,
    }

    ingest = ingest_live_captures(rebuild=True)
    report["images_ingested"] = ingest.added
    report["ingest"] = ingest.to_dict()

    feedback_n = export_feedback_pairs()
    report["feedback_pairs"] = feedback_n

    backup = CHECKPOINT_PRODUCTION.with_suffix(".pt.bak")
    if CHECKPOINT_PRODUCTION.is_file():
        shutil.copy2(CHECKPOINT_PRODUCTION, backup)

    prev = _load_previous_metrics()
    train_main(
        max_epochs=epochs,
        batch_size=batch_size,
        held_out_fold=None,
        checkpoint_path=CHECKPOINT_PRODUCTION,
        resume_from=CHECKPOINT_PRODUCTION if CHECKPOINT_PRODUCTION.is_file() else None,
        finetune=True,
    )

    metrics: dict = {}
    ckpt_metrics_path = CHECKPOINT_PRODUCTION
    if ckpt_metrics_path.is_file():
        import torch
        try:
            ckpt = torch.load(ckpt_metrics_path, map_location="cpu", weights_only=False)
        except TypeError:
            ckpt = torch.load(ckpt_metrics_path, map_location="cpu")
        metrics = ckpt.get("metrics", {})

    val_eer = float(metrics.get("eer", 1.0))
    val_rank1 = float(metrics.get("rank1_acc", 0.0))
    report["val_eer"] = val_eer
    report["val_rank1"] = val_rank1

    ok = True
    if prev and "val_eer" in prev:
        if val_eer > float(prev["val_eer"]) + EER_TOLERANCE:
            ok = False
            report["rollback_reason"] = f"EER {val_eer:.4f} worse than previous {prev['val_eer']:.4f}"
        if val_rank1 < float(prev.get("val_rank1", 0)) - RANK1_TOLERANCE:
            ok = False
            report["rollback_reason"] = report.get("rollback_reason", "") + f" Rank1 dropped to {val_rank1:.4f}"

    if not ok and backup.is_file():
        shutil.copy2(backup, CHECKPOINT_PRODUCTION)
        report["status"] = "rolled_back"
    else:
        report["status"] = "success"

    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    WEEKLY_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run_weekly_retrain()
