"""
Vein enhancement pipeline (Part 3 of PROJECT_PLAN.md), applied to the 224x224
ROI crops produced by roi_extraction.py.

Pipeline:
 1. CLAHE - local contrast boost. clipLimit=1.0 / tileGridSize=(16,16) chosen
    after a parameter sweep (see notes/day1/clahe_param_sweep.png) - the
    initially-tried clipLimit=2.0/tile=(8,8) produced a visible tile-boundary
    grid artifact on low-contrast (weak-visibility) images.
 2. Bilateral filter - edge-preserving denoise on the CLAHE output.
 3. Frangi vesselness (black_ridges=True - polarity verified in Day1 Task3/8,
    see notes/day1/frangi_polarity_check.png) on the bilateral-filtered image.
 4. Gabor filter bank (4 orientations: 0/45/90/135 degrees), max-combined,
    on the bilateral-filtered image.
 5. Each channel is normalized to [0, 1]:
    - Grayscale channel: per-image min-max (intensity range is already
      bounded and meaningful per-image, so this is fine).
    - Frangi/Gabor channels: normalized against FIXED GLOBAL scale constants
      (FRANGI_GLOBAL_SCALE, GABOR_GLOBAL_SCALE below), NOT per-image min-max.
      This was a deliberate fix after discovering that per-image min-max
      normalization makes weak-visibility images (where the true vesselness/
      Gabor signal is mostly noise) look like a strong, confident response,
      since min-max always stretches whatever tiny variation exists to fill
      [0,1] - see notes/day1/gabor_after_clahe_fix.png, where the grid-like
      noise pattern was being displayed as if it were strong signal. With a
      fixed global scale, a weak-visibility image's Frangi/Gabor channel
      correctly comes out mostly near-zero instead.
      The global scale constants were estimated as the 99.9th percentile of
      response values across a random sample of 150 images run through this
      exact pipeline (see scripts/calibrate_enhancement_scale.py output) -
      NOT the full 2,667-image dataset, so treat them as a reasonable
      starting estimate, not a final calibrated constant.
 6. Stacked into a 3-channel tensor analogous to an RGB image - compatible
    with ImageNet-pretrained backbones expected in Part 7.

This produces the per-image input tensor for model training; it does not
yet implement augmentation (Part 5, separate task) or the visibility-aware
fusion weighting (Part 4 - that lives at the attention/training level, not
in this preprocessing step).
"""
from pathlib import Path

import cv2
import numpy as np
from skimage.filters import frangi, gabor

CLAHE_CLIP_LIMIT = 1.0
CLAHE_TILE_GRID = (16, 16)
BILATERAL_D = 7
BILATERAL_SIGMA_COLOR = 50
BILATERAL_SIGMA_SPACE = 50
FRANGI_SIGMAS = range(1, 4, 1)
GABOR_FREQUENCY = 0.15
GABOR_THETAS = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

# Estimated as the 99.9th percentile of response values across a random
# 150-image sample run through this pipeline - see module docstring.
FRANGI_GLOBAL_SCALE = 0.6
GABOR_GLOBAL_SCALE = 0.055


def min_max_normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = arr.min(), arr.max()
    if hi - lo < 1e-12:
        return np.zeros_like(arr, dtype=np.float64)
    return (arr - lo) / (hi - lo)


def global_scale_normalize(arr: np.ndarray, scale: float) -> np.ndarray:
    return np.clip(arr / scale, 0.0, 1.0)


def enhance(roi_gray_uint8: np.ndarray, adversarial_defense: bool = False) -> np.ndarray:
    """roi_gray_uint8: 224x224 uint8 grayscale ROI. Returns 224x224x3 float64 in [0,1].

    adversarial_defense: if True, applies a light median blur before CLAHE.
    Task 9 (testing/reports/models/quicktier_*.md) found the model's input
    feature space is highly fragile to small gradient-based perturbations
    (FGSM eps=0.01 roughly halved own-class confidence) - those attacks rely
    on per-pixel sign noise far below the spatial scale of real vein ridges,
    so a small median filter destroys most of the adversarial signal while
    leaving genuine vein structure largely intact. Off by default because
    the production model was trained without it (forcing it on for every
    capture would shift the input distribution away from what the model was
    trained on); enable it for capture paths with real adversarial exposure
    (e.g. a network-facing API), not for routine enrollment/verification."""
    if adversarial_defense:
        roi_gray_uint8 = cv2.medianBlur(roi_gray_uint8, 3)

    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    clahe_img = clahe.apply(roi_gray_uint8)

    bilateral = cv2.bilateralFilter(clahe_img, BILATERAL_D, BILATERAL_SIGMA_COLOR, BILATERAL_SIGMA_SPACE)
    bilateral_f = bilateral.astype(np.float64) / 255.0

    frangi_resp = frangi(bilateral_f, sigmas=FRANGI_SIGMAS, black_ridges=True)

    gabor_responses = []
    for theta in GABOR_THETAS:
        real, _ = gabor(bilateral_f, frequency=GABOR_FREQUENCY, theta=theta)
        gabor_responses.append(np.abs(real))
    gabor_resp = np.max(np.stack(gabor_responses, axis=0), axis=0)

    channel_grayscale = min_max_normalize(clahe_img.astype(np.float64))
    channel_frangi = global_scale_normalize(frangi_resp, FRANGI_GLOBAL_SCALE)
    channel_gabor = global_scale_normalize(gabor_resp, GABOR_GLOBAL_SCALE)

    stacked = np.stack([channel_grayscale, channel_frangi, channel_gabor], axis=-1)
    return stacked


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from palm_vein.roi_extraction import extract_roi

    from palm_vein.config import PROJECT_ROOT, FIGURES_DIR

    project_root = PROJECT_ROOT
    samples = [
        "data/raw/img/005/Left/S1_005_L_1.png",
        "data/raw/img/020/Right/S1_020_R_1.png",
        "data/raw/img/108/Right/S2_108_R_2.png",
    ]

    fig, axes = plt.subplots(4, 3, figsize=(10, 12))
    for col, rel in enumerate(samples):
        img = cv2.imread(str(project_root / rel), cv2.IMREAD_GRAYSCALE)
        roi, _ = extract_roi(img)
        if roi is None:
            continue
        stacked = enhance(roi)

        axes[0, col].imshow(roi, cmap="gray")
        axes[0, col].set_title(f"{rel.split('/')[-1]}\nROI (input)", fontsize=8)
        axes[1, col].imshow(stacked[:, :, 0], cmap="gray")
        axes[1, col].set_title("Ch0: CLAHE grayscale", fontsize=8)
        axes[2, col].imshow(stacked[:, :, 1], cmap="hot")
        axes[2, col].set_title("Ch1: Frangi vesselness", fontsize=8)
        axes[3, col].imshow(stacked[:, :, 2], cmap="hot")
        axes[3, col].set_title("Ch2: Gabor response", fontsize=8)
        for row in range(4):
            axes[row, col].axis("off")

    plt.tight_layout()
    out_path = FIGURES_DIR / "vein_enhancement_comparison.png"
    plt.savefig(out_path, dpi=130)
    print(f"saved {out_path}")
