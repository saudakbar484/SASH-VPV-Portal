"""
PyTorch Dataset for the palm vein embedding model (Day 2 Task 6).

Two distinct splitting concepts are in play, and they must not be confused:
  1. The 5-fold CLASS-level split (cv_folds.csv, Day 2 Task 5) - which
     classes are held out entirely for open-set verification evaluation
     (Part 11, done in Day 2 Task 11). This dataset module takes a list of
     "available" classes (e.g. folds 1-4, with fold 0 reserved) and never
     touches the held-out fold's classes at all.
  2. Within those available classes, a small IMAGE-level holdout (last 2
     images per class, deterministic by sorted image_index) used only to
     monitor training progress / early-stop today's training loop. This is
     NOT the open-set evaluation - it's seen-class held-out images, useful
     as a fast proxy signal during training, while the real open-set EER
     evaluation against fully unseen classes happens in Day 2 Task 11.
     Conflating these two would be a methodological error (Day 1 Task 1 /
     Part 11's subject-leakage warning) - keeping them separate here is
     deliberate.

Training images go through: extract_roi -> augment -> enhance.
Validation images go through: extract_roi -> enhance (no augmentation,
deterministic, so validation metrics are stable across epochs).
"""
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from palm_vein.roi_extraction import extract_roi
from palm_vein.vein_enhancement import enhance
from palm_vein.augmentation import augment as augment_fn

from palm_vein.config import PROJECT_ROOT
N_HOLDOUT_PER_CLASS = 2


def to_tensor(stacked_hw3: np.ndarray) -> torch.Tensor:
    # (H, W, 3) float64 in [0,1] -> (3, H, W) float32 tensor.
    return torch.from_numpy(stacked_hw3.transpose(2, 0, 1).astype(np.float32))


class PalmVeinDataset(Dataset):
    def __init__(self, rows: List[dict], class_to_idx: dict, train: bool):
        self.rows = rows
        self.class_to_idx = class_to_idx
        self.train = train

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        row = self.rows[idx]
        img = cv2.imread(str(PROJECT_ROOT / row["relative_path"]), cv2.IMREAD_GRAYSCALE)
        roi, _ = extract_roi(img)
        if roi is None:
            # Landmark detection failed for this image (known limitation,
            # Day 1 Task 6/11) - fall back to a plain center-crop/resize
            # rather than crashing the whole training run on one bad image.
            roi = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
        if self.train:
            roi = augment_fn(roi)
        stacked = enhance(roi)
        tensor = to_tensor(stacked)
        label = self.class_to_idx[(row["subject_id"], row["hand"])]
        return tensor, label


def build_class_splits(visibility_rows: List[dict], excluded_fold_classes: set):
    """Returns (train_rows, val_rows, class_to_idx) for all classes NOT in excluded_fold_classes."""
    from collections import defaultdict

    by_class = defaultdict(list)
    for r in visibility_rows:
        key = (r["subject_id"], r["hand"])
        if key in excluded_fold_classes:
            continue
        by_class[key].append(r)

    class_keys = sorted(by_class.keys())
    class_to_idx = {key: i for i, key in enumerate(class_keys)}

    train_rows, val_rows = [], []
    for key, imgs in by_class.items():
        imgs_sorted = sorted(imgs, key=lambda r: int(r["image_index"]))
        if len(imgs_sorted) <= N_HOLDOUT_PER_CLASS:
            # Too few images to hold any out without starving training - use all for training.
            train_rows.extend(imgs_sorted)
            continue
        val_rows.extend(imgs_sorted[-N_HOLDOUT_PER_CLASS:])
        train_rows.extend(imgs_sorted[:-N_HOLDOUT_PER_CLASS])

    return train_rows, val_rows, class_to_idx
