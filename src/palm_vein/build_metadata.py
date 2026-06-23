"""
Regenerates dataset metadata for the SASH-VPV palm vein dataset by walking
Dataset/img/<subject>/<hand>/<filename>.png directly, since the original
folder_mapping.csv / palm_vein_dataset_*.csv referenced in Dataset/img/README.md
are not present in this copy of the dataset.

Filename convention observed: [Session]_[SubjectID]_[Hand]_[Index].png
e.g. S1_001_L_1.png
"""
import re
import csv
from pathlib import Path

from palm_vein.config import PROJECT_ROOT, DATA_RAW, METADATA_CSV

DATASET_ROOT = DATA_RAW
OUTPUT_CSV = METADATA_CSV

FILENAME_RE = re.compile(r"^(?P<session>S\d+)_(?P<subject>\d+)_(?P<hand_code>[LR])_(?P<index>\d+)\.png$", re.IGNORECASE)

rows = []
unmatched = []

for subject_dir in sorted(DATASET_ROOT.iterdir()):
    if not subject_dir.is_dir():
        continue
    subject_id = subject_dir.name

    for hand_dir in sorted(subject_dir.iterdir()):
        if not hand_dir.is_dir():
            continue
        # Normalize casing inconsistency: some folders are "Left"/"Right",
        # others are lowercase "left"/"right" (e.g. subjects 049, 053).
        hand_label = hand_dir.name.capitalize()
        if hand_label not in ("Left", "Right"):
            unmatched.append(str(hand_dir))
            continue

        non_standard_files = []
        for img_path in sorted(hand_dir.iterdir()):
            if img_path.suffix.lower() != ".png":
                continue
            m = FILENAME_RE.match(img_path.name)
            if not m:
                # Non-standard filename (e.g. timestamp-based, observed for
                # subjects 055, 070-Right, 121, 122). Don't drop the image -
                # record it with naming_convention="non_standard" and an
                # index assigned by sorted filename order within the folder.
                non_standard_files.append(img_path)
                continue

            session = m.group("session").upper()
            filename_subject = m.group("subject")
            hand_code = m.group("hand_code").upper()
            index = int(m.group("index"))

            if filename_subject != subject_id:
                # Folder name and filename subject ID disagree - flag, don't silently trust either.
                unmatched.append(f"subject_id mismatch: folder={subject_id} filename={filename_subject} path={img_path}")

            rows.append({
                "subject_id": subject_id,
                "hand": hand_label,
                "hand_code": hand_code,
                "session": session,
                "image_index": index,
                "filename": img_path.name,
                "relative_path": str(img_path.relative_to(PROJECT_ROOT)),
                "naming_convention": "standard",
            })

        for i, img_path in enumerate(non_standard_files, start=1):
            rows.append({
                "subject_id": subject_id,
                "hand": hand_label,
                "hand_code": hand_label[0].upper(),
                "session": "UNKNOWN",
                "image_index": i,
                "filename": img_path.name,
                "relative_path": str(img_path.relative_to(PROJECT_ROOT)),
                "naming_convention": "non_standard",
            })

rows.sort(key=lambda r: (r["subject_id"], r["hand"], r["image_index"]))

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["subject_id", "hand", "hand_code", "session", "image_index", "filename", "relative_path", "naming_convention"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")
print(f"Unmatched/flagged entries: {len(unmatched)}")
for u in unmatched[:20]:
    print("  -", u)

# Quick per-class image count summary (sanity check against README's stated 4-21 range)
from collections import Counter
class_counts = Counter((r["subject_id"], r["hand"]) for r in rows)
counts = list(class_counts.values())
print(f"Classes (subject x hand): {len(class_counts)}")
print(f"Min images/class: {min(counts)}, Max images/class: {max(counts)}, Avg: {sum(counts)/len(counts):.2f}")
