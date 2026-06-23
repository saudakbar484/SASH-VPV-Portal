"""
Subject-wise stratified 5-fold cross-validation split (Day 2 Task 5 / Part 11
of PROJECT_PLAN.md).

Critical design constraint: splitting happens at the CLASS level
(subject_id, hand), never at the image level. All images belonging to a
given subject's given hand go entirely into one fold. Splitting at the
image level would let the same physical hand appear in both train and
val/test, which would let the model "verify" a hand it has already
memorized rather than testing genuine generalization - this is the subject
leakage problem flagged in Day 1 Task 1 and Part 11 of the plan.

Stratification key: each class's majority (mode) vein-visibility tier from
visibility_tags.csv (Day 1 Task 3). This keeps strong/moderate/weak classes
roughly balanced across folds, so no fold ends up accidentally
all-weak-visibility. Session was considered as a secondary stratification
key but dropped here: 241/244 classes have a single consistent session
(verified directly - only 3 classes mix S1/S2/UNKNOWN), so session is
almost entirely determined by subject ID range already and stratifying on
it in addition to visibility would fragment the already-small per-stratum
counts (244 classes / 5 folds = ~49/fold) too much for StratifiedKFold to
handle cleanly.
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold

from palm_vein.config import PROJECT_ROOT, CV_FOLDS_CSV, VISIBILITY_CSV, METADATA_CSV, CHECKPOINT_PRODUCTION, CHECKPOINT_VALIDATION, CHECKPOINT_LEGACY, METRICS_DIR, FIGURES_DIR, DATA_RAW, CHECKPOINTS_DIR
N_SPLITS = 5
RANDOM_STATE = 42


def majority(values):
    return Counter(values).most_common(1)[0][0]


def main():
    with open(VISIBILITY_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_class = defaultdict(list)
    for r in rows:
        by_class[(r["subject_id"], r["hand"])].append(r)

    class_keys = sorted(by_class.keys())
    class_visibility = []
    class_session = []
    for key in class_keys:
        imgs = by_class[key]
        valid_visibility = [im["visibility_level"] for im in imgs if im["visibility_level"] != "unscored"]
        class_visibility.append(majority(valid_visibility) if valid_visibility else "unscored")
        class_session.append(majority([im["session"] for im in imgs]))

    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    fold_of_class = {}
    for fold_idx, (_, val_idx) in enumerate(skf.split(np.zeros(len(class_keys)), class_visibility)):
        for i in val_idx:
            fold_of_class[class_keys[i]] = fold_idx

    # Per-fold sanity report: class counts and visibility-tier balance.
    print("Per-fold class counts and visibility-tier distribution:")
    for fold_idx in range(N_SPLITS):
        keys_in_fold = [k for k, f in fold_of_class.items() if f == fold_idx]
        vis_counts = Counter(class_visibility[class_keys.index(k)] for k in keys_in_fold)
        print(f"  fold {fold_idx}: {len(keys_in_fold)} classes, visibility={dict(vis_counts)}")

    out_path = CV_FOLDS_CSV
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["subject_id", "hand", "session", "class_visibility_tier", "fold"])
        for key in class_keys:
            subject_id, hand = key
            idx = class_keys.index(key)
            writer.writerow([subject_id, hand, class_session[idx], class_visibility[idx], fold_of_class[key]])
    print(f"\nWrote {len(class_keys)} class-fold assignments to {out_path}")

    # Cross-check: no class should ever appear in more than one fold (by
    # construction this is guaranteed since fold_of_class is a dict keyed by
    # class, but verify explicitly rather than just trusting the logic).
    assert len(fold_of_class) == len(class_keys), "BUG: not every class got exactly one fold assignment"
    print("Verified: every class assigned to exactly one fold (no leakage by construction).")


if __name__ == "__main__":
    main()
