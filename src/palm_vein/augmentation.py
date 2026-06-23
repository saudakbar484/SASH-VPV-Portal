"""
Biometric-safe data augmentation (Part 5 of PROJECT_PLAN.md).

Applied to the 224x224 grayscale ROI (output of roi_extraction.py), BEFORE
vein_enhancement.enhance() - i.e. the training-time order is:
    raw image -> extract_roi() -> augment() -> enhance() -> model input

This ordering is deliberate: augmentation simulates capture-time variation
(hand tilt, distance, lighting, sensor noise), so it belongs at the stage
that represents "what the sensor captured," before the deterministic
Frangi/Gabor/CLAHE feature-extraction stage recomputes vessel/texture
channels from that (now-augmented) capture. Rotating a precomputed Frangi
map after the fact would be an approximation; recomputing Frangi/Gabor on
the augmented grayscale ROI is more faithful to what those filters would
actually see in a genuinely different capture.

Allowed transforms and ranges (identity-preserving, per Part 5):
  - rotation:     +/- 7 to 10 degrees
  - translation:  +/- 5% of ROI side (~+/- 11px at 224x224)
  - scaling:      +/- 5 to 8%
  - brightness:   +/- 10 to 15% multiplicative
  - contrast:     +/- 10 to 15% jitter
  - gaussian noise: sigma approx 2-5 (on 0-255 scale)

Explicitly NOT included: horizontal/vertical flips. A palm's vein graph is
not symmetric - flipping produces a vessel topology that never occurs
naturally for that subject, and could even make one subject's flipped
pattern coincidentally resemble a different subject's real pattern,
corrupting the label rather than just adding noise (see Part 5 of the plan
and notes/day1/04 below for the full reasoning).

Per Part 5, 1-3 of the above are composed per call (not all simultaneously),
chosen randomly, to avoid generating unrealistic combined distortions.
"""
from pathlib import Path

import cv2
import numpy as np

ROTATION_RANGE_DEG = (-10.0, 10.0)
TRANSLATION_FRACTION = 0.05      # of ROI side length
SCALE_RANGE = (0.92, 1.08)       # +/- 8%
BRIGHTNESS_RANGE = (0.85, 1.15)  # +/- 15% multiplicative
CONTRAST_RANGE = (0.85, 1.15)    # +/- 15%
GAUSSIAN_NOISE_SIGMA_RANGE = (2.0, 5.0)

AUGMENTATION_NAMES = ["rotate_translate_scale", "brightness", "contrast", "gaussian_noise"]


def _apply_geometric(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    h, w = img.shape[:2]
    angle = rng.uniform(*ROTATION_RANGE_DEG)
    scale = rng.uniform(*SCALE_RANGE)
    tx = rng.uniform(-TRANSLATION_FRACTION, TRANSLATION_FRACTION) * w
    ty = rng.uniform(-TRANSLATION_FRACTION, TRANSLATION_FRACTION) * h
    center = (w / 2.0, h / 2.0)
    M = cv2.getRotationMatrix2D(center, angle, scale)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=0)


def _apply_brightness(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    factor = rng.uniform(*BRIGHTNESS_RANGE)
    out = img.astype(np.float64) * factor
    return np.clip(out, 0, 255).astype(np.uint8)


def _apply_contrast(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    factor = rng.uniform(*CONTRAST_RANGE)
    mean = img.astype(np.float64).mean()
    out = (img.astype(np.float64) - mean) * factor + mean
    return np.clip(out, 0, 255).astype(np.uint8)


def _apply_gaussian_noise(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    sigma = rng.uniform(*GAUSSIAN_NOISE_SIGMA_RANGE)
    noise = rng.normal(0, sigma, size=img.shape)
    out = img.astype(np.float64) + noise
    return np.clip(out, 0, 255).astype(np.uint8)


_OPS = {
    "rotate_translate_scale": _apply_geometric,
    "brightness": _apply_brightness,
    "contrast": _apply_contrast,
    "gaussian_noise": _apply_gaussian_noise,
}


def augment(roi_uint8: np.ndarray, rng: np.random.Generator = None, n_ops: int = None) -> np.ndarray:
    """Apply 1-3 randomly chosen, identity-preserving augmentations to a 224x224 grayscale ROI."""
    if rng is None:
        rng = np.random.default_rng()
    if n_ops is None:
        n_ops = rng.integers(1, 4)  # 1, 2, or 3
    chosen = rng.choice(AUGMENTATION_NAMES, size=n_ops, replace=False)
    out = roi_uint8
    for name in chosen:
        out = _OPS[name](out, rng)
    return out


if __name__ == "__main__":
    import cv2 as cv
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from palm_vein.config import PROJECT_ROOT, FIGURES_DIR
    from palm_vein.roi_extraction import extract_roi

    sample = PROJECT_ROOT / "data/raw/img/005/Left/S1_005_L_1.png"
    img = cv.imread(str(sample), cv.IMREAD_GRAYSCALE)
    roi, _ = extract_roi(img)

    rng = np.random.default_rng(7)
    fig, axes = plt.subplots(1, 6, figsize=(15, 4))
    axes[0].imshow(roi, cmap="gray")
    axes[0].set_title("original ROI", fontsize=8)
    axes[0].axis("off")
    for i in range(1, 6):
        aug = augment(roi, rng)
        axes[i].imshow(aug, cmap="gray")
        axes[i].set_title(f"augmented #{i}", fontsize=8)
        axes[i].axis("off")
    plt.tight_layout()
    out_path = FIGURES_DIR / "augmentation_check.png"
    plt.savefig(out_path, dpi=130)
    print(f"saved {out_path}")
