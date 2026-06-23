"""
ROI normalization (Part 2, Stage 3 of PROJECT_PLAN.md): rotation correction +
scale normalization + translation alignment, producing a fixed-size 224x224
palm crop, built on top of segment_and_landmarks.find_landmarks().

Approach: combine rotation and scale into a single affine transform
(cv2.getRotationMatrix2D supports a scale factor directly), then crop a
fixed-size window centered on the transformed palm center.

 - Rotation angle: angle of the line between the two landmark (finger-valley)
   points relative to horizontal; rotating by the negative of this angle
   makes that line horizontal, removing hand-tilt variation.
 - Scale factor: TARGET_LANDMARK_DISTANCE_PX / actual landmark distance in
   the source image. This makes the inter-valley distance constant across
   all images regardless of hand size or capture distance (3-8cm range for
   this sensor), which is what "scale normalization" means here.
 - Translation: after rotation+scale, crop the fixed-size ROI_SIZE window
   centered on the transformed palm-center point (not the landmark
   midpoint), since palm center is more robust to finger spread than the
   landmark line's midpoint.

TARGET_LANDMARK_DISTANCE_PX=110 and ROI_SIZE=224 were chosen empirically by
visual inspection on 3 sample images (see notes/day1/roi_normalization_check.png)
so that the cropped window contains the full palm region without cutting off
the area between the landmarks and the wrist. This has NOT been tuned/verified
across the full dataset - recommend a wider visual QC pass (per the Day1 plan's
final review step) before treating these constants as final.
"""
from pathlib import Path

import cv2
import numpy as np

from palm_vein.segment_and_landmarks import find_landmarks, HandLandmarks

TARGET_LANDMARK_DISTANCE_PX = 110.0
ROI_SIZE = 224


def extract_roi(gray_img: np.ndarray, landmarks: HandLandmarks | None = None):
    if landmarks is None:
        landmarks = find_landmarks(gray_img)
    if landmarks.landmark_pair is None:
        return None, landmarks

    p1 = landmarks.contour_points[landmarks.landmark_pair[0]]
    p2 = landmarks.contour_points[landmarks.landmark_pair[1]]
    d = float(np.linalg.norm(p2 - p1))
    if d < 1e-6:
        return None, landmarks

    angle_rad = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    angle_deg = np.degrees(angle_rad)
    scale = TARGET_LANDMARK_DISTANCE_PX / d

    palm_center = landmarks.palm_center
    M = cv2.getRotationMatrix2D(center=palm_center, angle=angle_deg, scale=scale)

    h, w = gray_img.shape[:2]
    transformed = cv2.warpAffine(gray_img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)

    # palm_center maps to itself under a rotation/scale matrix centered there,
    # so the crop is just a fixed window around the original palm_center coords.
    cx, cy = palm_center
    half = ROI_SIZE // 2
    x0, y0 = int(round(cx - half)), int(round(cy - half))

    canvas = np.zeros((ROI_SIZE, ROI_SIZE), dtype=gray_img.dtype)
    src_x0, src_y0 = max(x0, 0), max(y0, 0)
    src_x1, src_y1 = min(x0 + ROI_SIZE, w), min(y0 + ROI_SIZE, h)
    dst_x0, dst_y0 = src_x0 - x0, src_y0 - y0
    dst_x1, dst_y1 = dst_x0 + (src_x1 - src_x0), dst_y0 + (src_y1 - src_y0)
    if src_x1 > src_x0 and src_y1 > src_y0:
        canvas[dst_y0:dst_y1, dst_x0:dst_x1] = transformed[src_y0:src_y1, src_x0:src_x1]

    return canvas, landmarks


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from palm_vein.config import PROJECT_ROOT, FIGURES_DIR

    samples = [
        "data/raw/img/005/Left/S1_005_L_1.png",
        "data/raw/img/020/Right/S1_020_R_1.png",
        "data/raw/img/100/Left/S2_100_L_1.png",
    ]

    fig, axes = plt.subplots(2, 3, figsize=(10, 7))
    for col, rel in enumerate(samples):
        img = cv2.imread(str(PROJECT_ROOT / rel), cv2.IMREAD_GRAYSCALE)
        roi, lm = extract_roi(img)
        axes[0, col].imshow(img, cmap="gray")
        axes[0, col].set_title(rel.split("/")[-1], fontsize=8)
        axes[0, col].axis("off")
        if roi is not None:
            axes[1, col].imshow(roi, cmap="gray")
            axes[1, col].set_title("224x224 ROI", fontsize=8)
        else:
            axes[1, col].set_title("ROI FAILED", fontsize=8)
        axes[1, col].axis("off")
    plt.tight_layout()
    out_path = FIGURES_DIR / "roi_normalization_check.png"
    plt.savefig(out_path, dpi=110)
    print(f"saved {out_path}")
