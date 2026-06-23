"""
Grad-CAM, Score-CAM, and CBAM attention-map visualization (Day 2 Task 10 /
Part 9 of PROJECT_PLAN.md), run against the trained checkpoint from Day 2
Task 8 (epoch 9, val_EER=0.024 on the 40-class subset).

Goal: verify the model is actually attending to vein/texture content rather
than ROI-crop borders, background, or sensor artifacts - directly checking
whether Day 1's known landmark-detection imperfections (some images get a
degraded/rotated crop) are something the model has learned to look past, or
something actively misleading it.

Target layer for both CAM methods: model.last_f4 (the post-CBAM stage-4
feature map, 320 channels at 7x7 spatial resolution) - the same feature map
that (after pooling, concatenation with stage3, and projection) becomes the
embedding. "Target score" for both: cosine similarity between the embedding
and the image's OWN ground-truth class weight vector in ArcFace - i.e. "how
much does this activation support the claim that this image is who it's
labeled as," which is the natural analogue of a classification logit for an
embedding model (see notes/day2/03).

Score-CAM is subsampled to the top-32 most-activated channels (by mean
activation magnitude) rather than all 320, for CPU compute feasibility -
documented in notes/day2/03 as a deliberate deviation from the textbook
all-channel method.
"""
import csv
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from palm_vein.model import PalmVeinEmbeddingNet, EMBED_DIM
from palm_vein.arcface_loss import ArcFaceLoss
from palm_vein.roi_extraction import extract_roi
from palm_vein.vein_enhancement import enhance
from palm_vein.dataset import to_tensor

from palm_vein.config import PROJECT_ROOT, CV_FOLDS_CSV, VISIBILITY_CSV, METADATA_CSV, CHECKPOINT_PRODUCTION, CHECKPOINT_VALIDATION, CHECKPOINT_LEGACY, METRICS_DIR, FIGURES_DIR, DATA_RAW, CHECKPOINTS_DIR
SCORE_CAM_TOP_K_CHANNELS = 32


def load_trained(checkpoint_path: Path):
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    class_to_idx = ckpt["class_to_idx"]
    model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    arcface = ArcFaceLoss(EMBED_DIM, len(class_to_idx))
    arcface.load_state_dict(ckpt["arcface_state_dict"])
    arcface.eval()
    return model, arcface, class_to_idx


def class_score(model, arcface, embedding, label_idx: int):
    normalized_weight = F.normalize(arcface.weight, p=2, dim=1)
    return (embedding @ normalized_weight[label_idx]).squeeze()


def grad_cam(model, arcface, x: torch.Tensor, label_idx: int) -> np.ndarray:
    model.zero_grad()
    embedding = model(x)
    score = class_score(model, arcface, embedding, label_idx)
    score.backward()

    f4 = model.last_f4  # (1, 320, 7, 7), grad populated via retain_grad in model.py
    grad = f4.grad
    weights = grad.mean(dim=(2, 3), keepdim=True)  # (1, 320, 1, 1)
    cam = F.relu((weights * f4.detach()).sum(dim=1, keepdim=True))  # (1,1,7,7)
    cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
    cam = cam.squeeze().numpy()
    if cam.max() > 1e-8:
        cam = cam / cam.max()
    return cam


def score_cam(model, arcface, x: torch.Tensor, label_idx: int, top_k: int = SCORE_CAM_TOP_K_CHANNELS) -> np.ndarray:
    with torch.no_grad():
        _ = model(x)
        f4 = model.last_f4.detach()  # (1, 320, 7, 7)

    channel_strength = f4.abs().mean(dim=(2, 3)).squeeze(0)  # (320,)
    top_idx = torch.topk(channel_strength, k=min(top_k, f4.shape[1])).indices

    cam = torch.zeros(224, 224)
    with torch.no_grad():
        for ch in top_idx:
            act = f4[0, ch:ch + 1].unsqueeze(0)  # (1,1,7,7)
            mask = F.interpolate(act, size=(224, 224), mode="bilinear", align_corners=False).squeeze()
            mask = (mask - mask.min()) / (mask.max() - mask.min() + 1e-8)
            masked_x = x * mask.unsqueeze(0).unsqueeze(0)
            embedding = model(masked_x)
            score = class_score(model, arcface, embedding, label_idx).item()
            cam += max(score, 0.0) * mask

    cam = cam.numpy()
    if cam.max() > 1e-8:
        cam = cam / cam.max()
    return cam


def get_cbam_spatial_gate(model) -> np.ndarray:
    gate = model.cbam_stage4.spatial_attention.last_gate  # (1,1,7,7)
    gate = F.interpolate(gate, size=(224, 224), mode="bilinear", align_corners=False)
    return gate.squeeze().numpy()


def prepare_input(relative_path: str):
    img = cv2.imread(str(PROJECT_ROOT / relative_path), cv2.IMREAD_GRAYSCALE)
    roi, _ = extract_roi(img)
    if roi is None:
        roi = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
    stacked = enhance(roi)
    tensor = to_tensor(stacked).unsqueeze(0)
    return roi, tensor


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    model, arcface, class_to_idx = load_trained(CHECKPOINT_PRODUCTION)
    available_classes = set(class_to_idx.keys())

    with open(VISIBILITY_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_tier = {"strong": [], "moderate": [], "weak": []}
    for r in rows:
        key = (r["subject_id"], r["hand"])
        if key in available_classes and r["visibility_level"] in by_tier:
            by_tier[r["visibility_level"]].append(r)

    import random
    random.seed(5)
    samples = []
    for tier in ["strong", "moderate", "weak"]:
        samples.extend(random.sample(by_tier[tier], min(2, len(by_tier[tier]))))

    fig, axes = plt.subplots(4, len(samples), figsize=(4 * len(samples), 13))
    for col, r in enumerate(samples):
        label_idx = class_to_idx[(r["subject_id"], r["hand"])]
        roi, x = prepare_input(r["relative_path"])

        gcam = grad_cam(model, arcface, x.clone(), label_idx)
        scam = score_cam(model, arcface, x.clone(), label_idx)
        cbam_map = get_cbam_spatial_gate(model)

        axes[0, col].imshow(roi, cmap="gray")
        axes[0, col].set_title(f"{r['visibility_level']}\n{Path(r['relative_path']).name}", fontsize=8)
        axes[1, col].imshow(roi, cmap="gray")
        axes[1, col].imshow(gcam, cmap="jet", alpha=0.45)
        axes[1, col].set_title("Grad-CAM", fontsize=8)
        axes[2, col].imshow(roi, cmap="gray")
        axes[2, col].imshow(scam, cmap="jet", alpha=0.45)
        axes[2, col].set_title(f"Score-CAM (top-{SCORE_CAM_TOP_K_CHANNELS} ch)", fontsize=8)
        axes[3, col].imshow(roi, cmap="gray")
        axes[3, col].imshow(cbam_map, cmap="jet", alpha=0.45)
        axes[3, col].set_title("CBAM spatial gate", fontsize=8)
        for row in range(4):
            axes[row, col].axis("off")

    plt.tight_layout()
    out_path = FIGURES_DIR / "explainability_grid.png"
    plt.savefig(out_path, dpi=120)
    print(f"saved {out_path}")
