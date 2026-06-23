"""
Training loop with anti-overfitting defenses (Day 2 Task 6 / Part 12 of
PROJECT_PLAN.md).

Defenses applied here:
  - Dropout (p=0.4, already inside PalmVeinEmbeddingNet's embedding head).
  - Weight decay (Adam optimizer's weight_decay arg, L2 penalty).
  - Label smoothing (passed into ArcFaceLoss - softens the one-hot target,
    discourages overconfident fitting to exact training labels).
  - Data augmentation (PalmVeinDataset applies augmentation.augment() on
    every training image - Day 1 Task 10).
  - Early stopping on validation EER (computed from held-out images of
    TRAINING-fold classes - see dataset.py's docstring for why this is a
    proxy metric, not the final open-set evaluation reserved for Task 11).

This script trains on 4 of the 5 folds from cv_folds.csv (Day 2 Task 5),
holding one fold's classes out entirely (never touched here) for the later
open-set verification evaluation in Day 2 Task 11.
"""
import csv
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.metrics import roc_curve, roc_auc_score

from palm_vein.arcface_loss import ArcFaceLoss
from palm_vein.dataset import PalmVeinDataset, build_class_splits
from palm_vein.model import PalmVeinEmbeddingNet, EMBED_DIM

from palm_vein.config import CV_FOLDS_CSV, VISIBILITY_CSV, CHECKPOINT_LEGACY, CHECKPOINT_PRODUCTION, DATA_PROCESSED
HELD_OUT_FOLD = 0  # reserved entirely for Day 2 Task 11's open-set evaluation
WEIGHT_DECAY = 1e-4
LABEL_SMOOTHING = 0.1
LEARNING_RATE = 1e-3
FINETUNE_LEARNING_RATE = 1e-4
EARLY_STOPPING_PATIENCE = 5
FEEDBACK_CSV = DATA_PROCESSED / "feedback_pairs.csv"


def compute_eer(genuine_scores: np.ndarray, impostor_scores: np.ndarray) -> float:
    y_true = np.concatenate([np.ones_like(genuine_scores), np.zeros_like(impostor_scores)])
    y_score = np.concatenate([genuine_scores, impostor_scores])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fnr = 1 - tpr
    idx = np.nanargmin(np.abs(fpr - fnr))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def gar_at_far(genuine_scores: np.ndarray, impostor_scores: np.ndarray, target_far: float) -> float:
    """GAR (genuine accept rate, i.e. TPR) at the threshold where impostor FAR <= target_far."""
    y_true = np.concatenate([np.ones_like(genuine_scores), np.zeros_like(impostor_scores)])
    y_score = np.concatenate([genuine_scores, impostor_scores])
    fpr, tpr, _ = roc_curve(y_true, y_score)
    valid = fpr <= target_far
    if not valid.any():
        return 0.0
    return float(tpr[valid].max())


def rank1_accuracy(embeddings: np.ndarray, labels: np.ndarray) -> float:
    """Rank-1 identification accuracy: for each class with >=2 val images,
    the first occurrence is the gallery entry, the rest are probes matched
    by nearest cosine similarity against all gallery entries."""
    by_label = defaultdict(list)
    for i, lab in enumerate(labels):
        by_label[lab].append(i)

    gallery_idx, gallery_labels = [], []
    probe_idx, probe_labels = [], []
    for lab, idxs in by_label.items():
        if len(idxs) < 2:
            continue  # no probe available for this class in this val set
        gallery_idx.append(idxs[0])
        gallery_labels.append(lab)
        for i in idxs[1:]:
            probe_idx.append(i)
            probe_labels.append(lab)

    if not gallery_idx or not probe_idx:
        return float("nan")

    gallery_emb = embeddings[gallery_idx]
    gallery_labels = np.array(gallery_labels)
    probe_emb = embeddings[probe_idx]
    probe_labels = np.array(probe_labels)

    sims = probe_emb @ gallery_emb.T  # (n_probe, n_gallery)
    pred_idx = sims.argmax(axis=1)
    pred_labels = gallery_labels[pred_idx]
    return float((pred_labels == probe_labels).mean())


def evaluate(model, val_loader, device) -> dict:
    model.eval()
    embeddings, labels = [], []
    with torch.no_grad():
        for x, y in val_loader:
            x = x.to(device)
            emb = model(x)
            embeddings.append(emb.cpu().numpy())
            labels.append(y.numpy())
    embeddings = np.concatenate(embeddings, axis=0)
    labels = np.concatenate(labels, axis=0)

    sim_matrix = embeddings @ embeddings.T
    n = len(labels)
    genuine, impostor = [], []
    for i in range(n):
        for j in range(i + 1, n):
            if labels[i] == labels[j]:
                genuine.append(sim_matrix[i, j])
            else:
                impostor.append(sim_matrix[i, j])

    if not genuine or not impostor:
        return {"eer": float("nan"), "roc_auc": float("nan"), "gar_at_far1pct": float("nan"), "rank1_acc": float("nan")}

    genuine = np.array(genuine)
    impostor = np.array(impostor)
    y_true = np.concatenate([np.ones_like(genuine), np.zeros_like(impostor)])
    y_score = np.concatenate([genuine, impostor])

    return {
        "eer": compute_eer(genuine, impostor),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "gar_at_far1pct": gar_at_far(genuine, impostor, target_far=0.01),
        "rank1_acc": rank1_accuracy(embeddings, labels),
    }


def load_data(fold_path: Path, visibility_path: Path, max_classes: int = None, seed: int = 123, held_out_fold: int = HELD_OUT_FOLD):
    with open(fold_path, newline="", encoding="utf-8") as f:
        fold_rows = list(csv.DictReader(f))
    # held_out_fold=None means no class is excluded (production run: train on
    # every available class, see gpu_training_package/PLAN.md stage 2).
    held_out_classes = set() if held_out_fold is None else \
        {(r["subject_id"], r["hand"]) for r in fold_rows if int(r["fold"]) == held_out_fold}

    with open(visibility_path, newline="", encoding="utf-8") as f:
        visibility_rows = list(csv.DictReader(f))

    train_rows, val_rows, class_to_idx = build_class_splits(visibility_rows, held_out_classes)

    if max_classes is not None and max_classes < len(class_to_idx):
        # Scoped-subset run (see Day 2 Task 8 notes): pick a fixed random
        # subset of classes so today's demo training pass finishes in a
        # practical amount of time on this CPU-only machine, rather than
        # the ~30 min/epoch the full class set would take (measured in
        # Day 2 Task 6's smoke test). NOT representative of full-dataset
        # convergence - just a mechanics/convergence-direction check.
        rng = np.random.default_rng(seed)
        all_classes = sorted(class_to_idx.keys())
        chosen = set(rng.choice(len(all_classes), size=max_classes, replace=False))
        chosen_classes = {all_classes[i] for i in chosen}
        class_to_idx = {c: i for i, c in enumerate(sorted(chosen_classes))}
        train_rows = [r for r in train_rows if (r["subject_id"], r["hand"]) in chosen_classes]
        val_rows = [r for r in val_rows if (r["subject_id"], r["hand"]) in chosen_classes]

    return train_rows, val_rows, class_to_idx


def _merge_arcface_weights(
    arcface: ArcFaceLoss,
    old_state: dict,
    old_class_to_idx: dict,
    new_class_to_idx: dict,
) -> None:
    """Copy overlapping class weights when fine-tuning with expanded gallery."""
    if "weight" not in old_state:
        return
    old_w = old_state["weight"]
    with torch.no_grad():
        for key, old_idx in old_class_to_idx.items():
            if key not in new_class_to_idx:
                continue
            new_idx = new_class_to_idx[key]
            if old_idx < old_w.shape[0] and new_idx < arcface.weight.shape[0]:
                arcface.weight.data[new_idx] = old_w[old_idx]


def main(
    max_epochs: int = 2,
    batch_size: int = 8,
    max_train_rows: int = None,
    max_val_rows: int = None,
    max_classes: int = None,
    held_out_fold: int | None = HELD_OUT_FOLD,
    checkpoint_path: Path | None = None,
    resume_from: Path | None = None,
    finetune: bool = False,
    export_feedback: bool = False,
):
    if export_feedback:
        from palm_vein.feedback_dataset import export_feedback_pairs
        n = export_feedback_pairs()
        print(f"Exported {n} feedback rows to {FEEDBACK_CSV}", flush=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}", flush=True)

    train_rows, val_rows, class_to_idx = load_data(
        CV_FOLDS_CSV, VISIBILITY_CSV,
        max_classes=max_classes, held_out_fold=held_out_fold,
    )
    if max_train_rows is not None:
        train_rows = train_rows[:max_train_rows]
    if max_val_rows is not None:
        val_rows = val_rows[:max_val_rows]
    num_classes = len(class_to_idx)
    fold_desc = "none (production: all classes)" if held_out_fold is None else str(held_out_fold)
    print(f"train images: {len(train_rows)}  val images: {len(val_rows)}  classes: {num_classes}  held_out_fold: {fold_desc}")

    train_ds = PalmVeinDataset(train_rows, class_to_idx, train=True)
    val_ds = PalmVeinDataset(val_rows, class_to_idx, train=False)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    lr = FINETUNE_LEARNING_RATE if finetune or resume_from else LEARNING_RATE
    pretrained_backbone = not (finetune or resume_from)

    model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=pretrained_backbone).to(device)
    arcface = ArcFaceLoss(EMBED_DIM, num_classes, label_smoothing=LABEL_SMOOTHING).to(device)

    resume_path = resume_from or (CHECKPOINT_PRODUCTION if finetune else None)
    if resume_path and Path(resume_path).is_file():
        try:
            ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        except TypeError:
            ckpt = torch.load(resume_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"], strict=True)
        old_cti = ckpt.get("class_to_idx", {})
        if isinstance(old_cti, dict):
            _merge_arcface_weights(arcface, ckpt.get("arcface_state_dict", {}), old_cti, class_to_idx)
        print(f"Resumed embedding weights from {resume_path}", flush=True)

    optimizer = torch.optim.Adam(
        list(model.parameters()) + list(arcface.parameters()),
        lr=lr, weight_decay=WEIGHT_DECAY,
    )

    best_eer = float("inf")
    epochs_without_improvement = 0
    if checkpoint_path is None:
        checkpoint_path = CHECKPOINT_LEGACY
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(max_epochs):
        model.train()
        t0 = time.time()
        total_loss = 0.0
        n_batches = 0
        n_correct = 0
        n_seen = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            embeddings = model(x)
            loss = arcface(embeddings, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
            with torch.no_grad():
                preds = arcface.predict_logits(embeddings).argmax(dim=1)
                n_correct += (preds == y).sum().item()
                n_seen += y.size(0)
        avg_loss = total_loss / max(n_batches, 1)
        train_acc = n_correct / max(n_seen, 1)

        metrics = evaluate(model, val_loader, device)
        elapsed = time.time() - t0
        print(
            f"epoch {epoch+1}/{max_epochs}  train_loss={avg_loss:.4f}  train_acc={train_acc:.4f}  "
            f"val_EER={metrics['eer']:.4f}  val_ROC_AUC={metrics['roc_auc']:.4f}  "
            f"val_GAR@FAR1%={metrics['gar_at_far1pct']:.4f}  val_Rank1={metrics['rank1_acc']:.4f}  ({elapsed:.1f}s)",
            flush=True,
        )

        val_eer = metrics["eer"]
        if val_eer < best_eer:
            best_eer = val_eer
            epochs_without_improvement = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "arcface_state_dict": arcface.state_dict(),
                "class_to_idx": class_to_idx,
                "epoch": epoch,
                "metrics": metrics,
                "train_loss": avg_loss,
                "train_acc": train_acc,
            }, checkpoint_path)
            print(f"  -> new best val_EER, saved checkpoint to {checkpoint_path}")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= EARLY_STOPPING_PATIENCE:
                print(f"Early stopping at epoch {epoch+1} (no improvement for {EARLY_STOPPING_PATIENCE} epochs)")
                break

    print(f"Training loop finished. Best val_EER: {best_eer:.4f}")


if __name__ == "__main__":
    # Smoke test only - confirms the loop runs end-to-end without crashing,
    # on a small subset and few epochs. The real training run (more epochs,
    # full data) is Day 2 Task 8.
    main(max_epochs=2, batch_size=4, max_train_rows=40, max_val_rows=20)
