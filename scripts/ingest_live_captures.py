#!/usr/bin/env python3
"""CLI: ingest live enrollment images into data/raw/img and rebuild metadata."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from palm_vein.ingest_live import ingest_live_captures  # noqa: E402


def main() -> None:
    report = ingest_live_captures(rebuild=True)
    print(report.to_dict())


if __name__ == "__main__":
    main()
