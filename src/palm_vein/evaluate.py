"""
Day 2 Task 11: full evaluation framework (Part 10/11 of PROJECT_PLAN.md),
run against the genuinely held-out fold-0 classes (49 classes / 547 images)
from cv_folds.csv - these classes were NEVER touched during Day 2 Task 8's
training run, so this is a true open-set evaluation, unlike Task 6/8's
seen-class validation EER (which was only a training-time proxy metric).

Scope honesty: this evaluates ONE trained model against ONE held-out fold
(fold 0), not the full 5-fold mean+-std sweep Part 11 describes. A true
5-fold sweep would mean training 5 separate models (one per held-out fold),
which at ~125-270s/epoch x several epochs x 5 folds is multiple hours on
this CPU-only machine - not done in this session. This script's evaluation
is real and methodologically sound (genuinely unseen classes), but it is a
single-fold estimate, not a cross-validated one - report any metric here
with that caveat, not as a final cross-validated number.

Also note: only the embedding model (PalmVeinEmbeddingNet) is used here,
NOT the trained ArcFace classifier head - ArcFace's per-class weight
vectors are specific to the 40 TRAINING classes and have no meaning for
fold-0's unseen classes. Open-set evaluation only ever uses the embedding
space + cosine similarity, never the classifier head - this is the whole
point of metric learning (Day 2 Task 1).

Metrics produced: EER, ROC-AUC, GAR@FAR=1%, GAR@FAR=0.1%, Rank-1, Rank-5
accuracy, plus a cosine-similarity-distribution histogram and t-SNE/UMAP
embedding visualizations colored by identity.

Deliverable note: an actual executed .ipynb is not produced here (no
notebook-execution tool available in this session) - this script + its
output plots/CSV are the practical equivalent: metrics.csv,
similarity_distribution.png, tsne_umap.png.
"""
import csv
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from sklearn.manifold import TSNE
from sklearn.metrics import roc_curve, roc_auc_score
import umap

from palm_vein.model import PalmVeinEmbeddingNet, EMBED_DIM
from palm_vein.roi_extraction import extract_roi
from palm_vein.vein_enhancement import enhance
from palm_vein.dataset import to_tensor

from palm_vein.config import PROJECT_ROOT, CV_FOLDS_CSV, VISIBILITY_CSV, METADATA_CSV, CHECKPOINT_PRODUCTION, CHECKPOINT_VALIDATION, CHECKPOINT_LEGACY, METRICS_DIR, FIGURES_DIR, DATA_RAW, CHECKPOINTS_DIR
HELD_OUT_FOLD = 0


def compute_eer(genuine_scores: np.ndarray, impostor_scores: np.ndarray) -> float:
    y_true = np.concatenate([np.ones_like(genuine_scores), np.zeros_like(impostor_scores)])
    y_score = np.concatenate([genuine_scores, impostor_scores])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fnr = 1 - tpr
    idx = np.nanargmin(np.abs(fpr - fnr))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def gar_at_far(genuine_scores: np.ndarray, impostor_scores: np.ndarray, target_far: float) -> float:
    y_true = np.concatenate([np.ones_like(genuine_scores), np.zeros_like(impostor_scores)])
    y_score = np.concatenate([genuine_scores, impostor_scores])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    valid = fpr <= target_far
    if not valid.any():
        return 0.0
    return float(tpr[valid].max())


def rank_k_accuracy(embeddings: np.ndarray, labels: np.ndarray, k_values=(1, 5)) -> dict:
    """Gallery = first image (by sorted image_index) per class, probe = the rest."""
    by_label = defaultdict(list)
    for i, lab in enumerate(labels):
        by_label[lab].append(i)

    gallery_idx, gallery_labels = [], []
    probe_idx, probe_labels = [], []
    for lab, idxs in by_label.items():
        if len(idxs) < 2:
            continue
        gallery_idx.append(idxs[0])
        gallery_labels.append(lab)
        for i in idxs[1:]:
            probe_idx.append(i)
            probe_labels.append(lab)

    gallery_emb = embeddings[gallery_idx]
    gallery_labels = np.array(gallery_labels)
    probe_emb = embeddings[probe_idx]
    probe_labels = np.array(probe_labels)

    sims = probe_emb @ gallery_emb.T  # (n_probe, n_gallery)
    order = np.argsort(-sims, axis=1)  # descending similarity
    ranked_labels = gallery_labels[order]  # (n_probe, n_gallery) labels in rank order

    results = {}
    for k in k_values:
        topk = ranked_labels[:, :k]
        hit = (topk == probe_labels[:, None]).any(axis=1)
        results[f"rank{k}_acc"] = float(hit.mean())
    return results


def main():
    with open(CV_FOLDS_CSV, newline="", encoding="utf-8") as f:
        fold_rows = list(csv.DictReader(f))
    held_out_classes = {(r["subject_id"], r["hand"]) for r in fold_rows if int(r["fold"]) == HELD_OUT_FOLD}

    with open(VISIBILITY_CSV, newline="", encoding="utf-8") as f:
        visibility_rows = list(csv.DictReader(f))
    fold0_rows = [r for r in visibility_rows if (r["subject_id"], r["hand"]) in held_out_classes]
    print(f"Held-out fold {HELD_OUT_FOLD}: {len(held_out_classes)} classes, {len(fold0_rows)} images")

    label_map = {key: i for i, key in enumerate(sorted(held_out_classes))}

    ckpt = torch.load(CHECKPOINT_PRODUCTION, map_location="cpu")
    model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    embeddings, labels = [], []
    t0 = time.time()
    for i, r in enumerate(fold0_rows):
        img = cv2.imread(str(PROJECT_ROOT / r["relative_path"]), cv2.IMREAD_GRAYSCALE)
        roi, _ = extract_roi(img)
        if roi is None:
            roi = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)
        stacked = enhance(roi)
        x = to_tensor(stacked).unsqueeze(0)
        with torch.no_grad():
            emb = model(x).squeeze(0).numpy()
        embeddings.append(emb)
        labels.append(label_map[(r["subject_id"], r["hand"])])
        if (i + 1) % 100 == 0:
            print(f"  embedded {i+1}/{len(fold0_rows)} ({time.time()-t0:.1f}s elapsed)", flush=True)

    embeddings = np.stack(embeddings)
    labels = np.array(labels)
    print(f"Computed {len(embeddings)} embeddings in {time.time()-t0:.1f}s")

    sim_matrix = embeddings @ embeddings.T
    n = len(labels)
    genuine, impostor = [], []
    for i in range(n):
        for j in range(i + 1, n):
            (genuine if labels[i] == labels[j] else impostor).append(sim_matrix[i, j])
    genuine = np.array(genuine)
    impostor = np.array(impostor)
    print(f"Genuine pairs: {len(genuine)}  Impostor pairs: {len(impostor)}")

    y_true = np.concatenate([np.ones_like(genuine), np.zeros_like(impostor)])
    y_score = np.concatenate([genuine, impostor])

    metrics = {
        "n_classes": len(held_out_classes),
        "n_images": len(fold0_rows),
        "n_genuine_pairs": len(genuine),
        "n_impostor_pairs": len(impostor),
        "eer": compute_eer(genuine, impostor),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "gar_at_far1pct": gar_at_far(genuine, impostor, 0.01),
        "gar_at_far0.1pct": gar_at_far(genuine, impostor, 0.001),
    }
    metrics.update(rank_k_accuracy(embeddings, labels, k_values=(1, 5)))

    print("\n=== Open-set evaluation on held-out fold (genuinely unseen classes) ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    with open(METRICS_DIR / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in metrics.items():
            writer.writerow([k, v])
    print(f"\nSaved metrics to {METRICS_DIR / 'metrics.csv'}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(impostor, bins=50, alpha=0.6, label="impostor pairs", color="crimson", density=True)
    ax.hist(genuine, bins=50, alpha=0.6, label="genuine pairs", color="seagreen", density=True)
    ax.set_xlabel("cosine similarity")
    ax.set_ylabel("density")
    ax.set_title(f"Genuine vs impostor similarity (held-out fold {HELD_OUT_FOLD}, EER={metrics['eer']:.3f})")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "similarity_distribution.png", dpi=130)
    print("Saved similarity_distribution.png")

    print("Running t-SNE...", flush=True)
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, n // 4))
    tsne_emb = tsne.fit_transform(embeddings)

    print("Running UMAP...", flush=True)
    reducer = umap.UMAP(n_components=2, random_state=42)
    umap_emb = reducer.fit_transform(embeddings)

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    sc0 = axes[0].scatter(tsne_emb[:, 0], tsne_emb[:, 1], c=labels, cmap="tab20", s=15)
    axes[0].set_title("t-SNE of held-out-fold embeddings (colored by identity)")
    sc1 = axes[1].scatter(umap_emb[:, 0], umap_emb[:, 1], c=labels, cmap="tab20", s=15)
    axes[1].set_title("UMAP of held-out-fold embeddings (colored by identity)")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "tsne_umap.png", dpi=130)
    print("Saved tsne_umap.png")


if __name__ == "__main__":
    main()
