"""
Estimates global normalization scale constants for the Frangi/Gabor channels
in vein_enhancement.py, by sampling a subset of images, running them through
the actual ROI + CLAHE + bilateral + Frangi/Gabor pipeline, and reporting
percentiles of the response distribution.

Why this exists: per-image min-max normalization of the Frangi/Gabor channels
makes weak-visibility images (where the true signal is mostly noise) look
like confident, full-range responses - discovered while building
vein_enhancement.py (see notes/day1/gabor_after_clahe_fix.png). Using a fixed
global scale instead means weak images correctly come out mostly near-zero.

This script only samples 150/2667 images for speed - rerun with a larger
sample (or the full dataset) if you need a more precise calibration; the
constants currently hardcoded in vein_enhancement.py came from one run of
this script with random.seed(42).
"""
import csv
import random
from pathlib import Path

import cv2
import numpy as np
from skimage.filters import frangi, gabor

from palm_vein.roi_extraction import extract_roi

from palm_vein.config import PROJECT_ROOT, CV_FOLDS_CSV, VISIBILITY_CSV, METADATA_CSV, CHECKPOINT_PRODUCTION, CHECKPOINT_VALIDATION, CHECKPOINT_LEGACY, METRICS_DIR, FIGURES_DIR, DATA_RAW, CHECKPOINTS_DIR
SAMPLE_SIZE = 150
SEED = 42

CLAHE_CLIP_LIMIT = 1.0
CLAHE_TILE_GRID = (16, 16)
FRANGI_SIGMAS = range(1, 4, 1)
GABOR_FREQUENCY = 0.15
GABOR_THETAS = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]


def main():
    with open(METADATA_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    random.seed(SEED)
    sample = random.sample(rows, SAMPLE_SIZE)

    frangi_vals, gabor_vals = [], []
    for r in sample:
        img = cv2.imread(str(PROJECT_ROOT / r["relative_path"]), cv2.IMREAD_GRAYSCALE)
        roi, _ = extract_roi(img)
        if roi is None:
            continue
        clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
        clahe_img = clahe.apply(roi)
        bilateral = cv2.bilateralFilter(clahe_img, 7, 50, 50)
        bf = bilateral.astype(np.float64) / 255.0
        fr = frangi(bf, sigmas=FRANGI_SIGMAS, black_ridges=True)
        gb = np.max(np.stack([np.abs(gabor(bf, frequency=GABOR_FREQUENCY, theta=t)[0]) for t in GABOR_THETAS], axis=0), axis=0)
        frangi_vals.append(fr)
        gabor_vals.append(gb)

    frangi_all = np.concatenate([f.ravel() for f in frangi_vals])
    gabor_all = np.concatenate([g.ravel() for g in gabor_vals])
    for name, arr in [("frangi", frangi_all), ("gabor", gabor_all)]:
        print(f"{name}: p50={np.percentile(arr,50):.6f} p95={np.percentile(arr,95):.6f} "
              f"p99={np.percentile(arr,99):.6f} p99.9={np.percentile(arr,99.9):.6f} max={arr.max():.6f}")


if __name__ == "__main__":
    main()
