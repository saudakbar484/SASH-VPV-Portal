"""
Hand segmentation + palm localization (Part 2, Stage 1-2 of PROJECT_PLAN.md).

Pipeline, validated visually against 3 sample images spanning both hands and
both sessions (see notes/day1/landmark_detection_filtered.png) before being
finalized here:

 1. Otsu threshold -> binary foreground mask, cleaned with a morphological
    close+open pass (closes small dark gaps inside the hand, removes small
    bright speckle noise outside it).
 2. Largest external contour = hand silhouette.
 3. Radial distance-from-centroid profile around the contour; fingertips are
    local maxima, finger valleys are local minima (scipy.signal.find_peaks).
 4. Candidates are restricted to the "finger half" of the contour, determined
    via the hand silhouette's PCA principal axis rather than a fixed
    image-y cutoff (see `_finger_side_sign` below). This was changed after
    Quick Tier Task 3 (testing/reports/models/quicktier_*.md) quantified
    that alignment error grows sharply with rotation (5.9px at 5 deg up to
    21.3px at 15 deg) - a fixed "points above centroid in image-y" filter
    silently drops valid valleys once the hand is rotated enough that
    fingers no longer point toward the top of the frame. The PCA-axis
    version adapts to whatever orientation the hand actually has in a given
    capture, instead of assuming "up".
 5. Landmark pair = the leftmost and rightmost detected valley above the
    centroid (typically thumb-index and ring-pinky boundaries, though this
    is a positional heuristic, not finger-identity classification - it has
    NOT been verified to always pick the textbook-recommended index-middle /
    ring-pinky pair specifically).
 6. Palm center = point of maximum value in the distance transform of the
    mask (center of the largest inscribed circle) - robust to finger
    position since it depends on the palm's solid interior, not the contour.

Known limitation: if fewer than 2 valleys are detected above the centroid
(e.g. a poorly segmented or heavily cropped hand), landmark_pair is None -
callers must handle this case (skip the image, or fall back to a
bounding-box-only crop) rather than assuming landmarks always exist.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks


@dataclass
class HandLandmarks:
    mask: np.ndarray
    contour_points: np.ndarray       # (N, 2) contour points in (x, y)
    centroid: tuple                  # (cx, cy)
    palm_center: tuple               # (px, py)
    fingertip_indices: np.ndarray    # indices into contour_points
    valley_indices: np.ndarray       # indices into contour_points (candidates)
    landmark_pair: tuple | None      # (idx_left, idx_right) into contour_points, or None


def segment_hand(gray_img: np.ndarray) -> np.ndarray:
    _, mask = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return mask


def _finger_side_sign(pts: np.ndarray, cx: float, cy: float, dist: np.ndarray, axis: np.ndarray):
    """Projects contour points onto the hand's PCA principal axis and returns
    (sign, proj) where `sign * proj[i] > 0` selects the finger half. The sign
    is picked as whichever side the highest-radial-distance points (i.e. the
    fingertip-like contour points) concentrate on - this works regardless of
    how the hand is rotated in the frame, unlike a fixed image-y cutoff."""
    proj = (pts[:, 0] - cx) * axis[0] + (pts[:, 1] - cy) * axis[1]
    n_top = max(5, len(dist) // 10)
    top_idx = np.argsort(dist)[-n_top:]
    sign = 1.0 if np.mean(proj[top_idx]) >= 0 else -1.0
    return sign, proj


def find_landmarks(gray_img: np.ndarray) -> HandLandmarks:
    mask = segment_hand(gray_img)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError("No contour found - check input image / segmentation.")
    contour = max(contours, key=cv2.contourArea)

    M = cv2.moments(contour)
    if M["m00"] == 0:
        raise ValueError("Degenerate contour (zero area).")
    cx, cy = M["m10"] / M["m00"], M["m01"] / M["m00"]

    pts = contour.reshape(-1, 2).astype(np.float64)
    dist = np.sqrt((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2)

    # Pad for wrap-around so peaks/valleys near the contour's start/end index aren't missed.
    pad = min(50, len(dist) - 1)
    d_ext = np.concatenate([dist, dist[:pad]])
    peak_idx, _ = find_peaks(d_ext, distance=20, prominence=10)
    valley_idx, _ = find_peaks(-d_ext, distance=20, prominence=10)
    peak_idx = peak_idx[peak_idx < len(dist)]
    valley_idx = valley_idx[valley_idx < len(dist)]

    # Restrict to the finger half of the contour via the PCA principal axis,
    # rotation-invariant (see module docstring and _finger_side_sign).
    _, eigenvectors, _ = cv2.PCACompute2(pts.astype(np.float32), mean=np.array([[cx, cy]], dtype=np.float32))
    principal_axis = eigenvectors[0]
    sign, proj = _finger_side_sign(pts, cx, cy, dist, principal_axis)
    peak_idx = np.array([i for i in peak_idx if sign * proj[i] > 0], dtype=int)
    valley_idx = np.array([i for i in valley_idx if sign * proj[i] > 0], dtype=int)

    dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(dist_transform)

    landmark_pair = None
    if len(valley_idx) >= 2:
        ordered = valley_idx[np.argsort(pts[valley_idx, 0])]
        landmark_pair = (int(ordered[0]), int(ordered[-1]))

    return HandLandmarks(
        mask=mask,
        contour_points=pts,
        centroid=(cx, cy),
        palm_center=max_loc,
        fingertip_indices=peak_idx,
        valley_indices=valley_idx,
        landmark_pair=landmark_pair,
    )


if __name__ == "__main__":
    from palm_vein.config import PROJECT_ROOT

    samples = [
        "data/raw/img/005/Left/S1_005_L_1.png",
        "data/raw/img/020/Right/S1_020_R_1.png",
        "data/raw/img/100/Left/S2_100_L_1.png",
    ]
    for rel in samples:
        img = cv2.imread(str(PROJECT_ROOT / rel), cv2.IMREAD_GRAYSCALE)
        lm = find_landmarks(img)
        status = "OK" if lm.landmark_pair else "NO LANDMARK PAIR FOUND"
        print(f"{rel}: fingertips={len(lm.fingertip_indices)} valleys={len(lm.valley_indices)} "
              f"palm_center={lm.palm_center} -> {status}")
