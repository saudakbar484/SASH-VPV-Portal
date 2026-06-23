"""
Tags each palm image with a vein-visibility level (strong/moderate/weak) using
a quick Frangi-vesselness heuristic, as a fast proxy for manual labeling.

Method (verified on a sample image before running on the full dataset):
 1. Downsample to half resolution (480x640 -> 240x320) purely for speed -
    visual check confirmed line/vessel structures are still resolvable.
 2. Otsu threshold to get a hand foreground mask, then erode it by a fixed
    margin. This step matters: an un-eroded mask lets the strong
    hand-silhouette boundary edge dominate the vesselness signal (confirmed
    visually - see notes/day1/frangi_eroded_check.png), which would make this
    a "hand edge sharpness" metric instead of a vein-visibility metric.
 3. Run skimage.filters.frangi(black_ridges=True) - confirmed correct
    polarity visually (notes/day1/frangi_polarity_check.png): veins/lines
    appear as dark ridges on lighter skin in this NIR captures, not bright
    ridges.
 4. Summarize with mean and 90th-percentile vesselness response inside the
    eroded mask.
 5. After scoring every image, classify into strong/moderate/weak by tertile
    (33rd/66th percentile) of the mean-vesselness distribution across the
    WHOLE dataset. This is a heuristic relative ranking, not an
    absolutely-calibrated visibility scale - it has not been validated
    against human-labeled ground truth. Recommend spot-checking a sample of
    each tier manually before trusting it for stratified splitting.
"""
import csv
import time
from pathlib import Path

import cv2
import numpy as np
from skimage.filters import frangi

from palm_vein.config import PROJECT_ROOT, DATA_RAW, METADATA_CSV, VISIBILITY_CSV

DATASET_ROOT = DATA_RAW
OUTPUT_CSV = VISIBILITY_CSV

ERODE_KERNEL = np.ones((25, 25), np.uint8)
SIGMAS = range(1, 4, 1)


def score_image(img_path: Path):
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    small = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
    _, mask = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    eroded = cv2.erode(mask, ERODE_KERNEL, iterations=1)
    fg = eroded > 0
    if fg.sum() < 200:
        # Erosion ate almost everything (very small/poorly segmented hand) -
        # fall back to the un-eroded mask rather than scoring on ~nothing.
        fg = mask > 0
        if fg.sum() < 50:
            return None

    small_f = small.astype(np.float64) / 255.0
    vess = frangi(small_f, sigmas=SIGMAS, black_ridges=True)
    values = vess[fg]
    return float(values.mean()), float(np.percentile(values, 90))


def main():
    with open(METADATA_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        meta_rows = list(reader)

    results = []
    t0 = time.time()
    for i, row in enumerate(meta_rows, start=1):
        img_path = PROJECT_ROOT / row["relative_path"]
        scores = score_image(img_path)
        if scores is None:
            mean_v, p90_v = float("nan"), float("nan")
        else:
            mean_v, p90_v = scores
        results.append({**row, "mean_vesselness": mean_v, "p90_vesselness": p90_v})
        if i % 200 == 0:
            elapsed = time.time() - t0
            print(f"  processed {i}/{len(meta_rows)} ({elapsed:.1f}s elapsed)")

    valid = [r for r in results if r["mean_vesselness"] == r["mean_vesselness"]]  # filter NaN
    means = np.array([r["mean_vesselness"] for r in valid])
    t33, t66 = np.percentile(means, [33.33, 66.66])
    print(f"Tertile thresholds: t33={t33:.6f}, t66={t66:.6f}")

    for r in results:
        mv = r["mean_vesselness"]
        if mv != mv:
            r["visibility_level"] = "unscored"
        elif mv < t33:
            r["visibility_level"] = "weak"
        elif mv < t66:
            r["visibility_level"] = "moderate"
        else:
            r["visibility_level"] = "strong"

    fieldnames = list(meta_rows[0].keys()) + ["mean_vesselness", "p90_vesselness", "visibility_level"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {len(results)} rows to {OUTPUT_CSV}")
    from collections import Counter
    print(Counter(r["visibility_level"] for r in results))
    print(f"Total time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
