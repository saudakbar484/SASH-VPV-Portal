"""folder_mapping.csv helpers — maps dataset folder ids to registered users."""
from __future__ import annotations

import csv
from pathlib import Path

from backend.settings import DATASET_DIR, FOLDER_MAPPING_CSV

CSV_HEADERS = [
    "folder_id",
    "dataset_name",
    "email",
    "full_name",
    "account_id",
]


def ensure_csv() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    if not FOLDER_MAPPING_CSV.exists():
        with FOLDER_MAPPING_CSV.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def read_rows() -> list[dict[str, str]]:
    ensure_csv()
    with FOLDER_MAPPING_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def email_exists(email: str) -> bool:
    email_l = email.strip().lower()
    return any(r.get("email", "").lower() == email_l for r in read_rows())


def dataset_name_taken(name: str) -> bool:
    name_l = name.strip().lower()
    return any(r.get("dataset_name", "").lower() == name_l for r in read_rows())


def next_folder_id() -> str:
    """Allocate the next 3-digit folder id (001, 002, … 070, …)."""
    ensure_csv()
    used: set[int] = set()
    for row in read_rows():
        try:
            used.add(int(row["folder_id"]))
        except (KeyError, ValueError):
            continue
    for sub in DATASET_DIR.iterdir():
        if sub.is_dir() and sub.name.isdigit():
            used.add(int(sub.name))
    n = max(used) + 1 if used else 1
    return f"{n:03d}"


def append_row(
    *,
    folder_id: str,
    dataset_name: str,
    email: str,
    full_name: str,
    account_id: int,
) -> None:
    ensure_csv()
    with FOLDER_MAPPING_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([folder_id, dataset_name, email, full_name, account_id])
