"""
Test live captures against the production model's trained identity gallery.

Since test photos are from a user already present in the training dataset,
each image is classified against all 244 enrolled (subject, hand) identities
using the checkpoint's ArcFace head (cosine similarity to class weights).
"""
import _bootstrap  # noqa: F401

from pathlib import Path

import torch

from palm_vein.arcface_loss import ArcFaceLoss
from palm_vein.config import CHECKPOINT_PRODUCTION, LIVE_ENROLL_DIR
from palm_vein.deployment import CaptureQualityError, PalmVeinBiometricSystem, DEFAULT_THRESHOLD
from palm_vein.model import EMBED_DIM, PalmVeinEmbeddingNet

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def collect_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def load_classifier(checkpoint_path: Path):
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    class_to_idx = ckpt["class_to_idx"]
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    num_classes = len(class_to_idx)
    arcface = ArcFaceLoss(EMBED_DIM, num_classes)
    arcface.load_state_dict(ckpt["arcface_state_dict"])
    arcface.eval()

    return model, arcface, idx_to_class


def predict_identity(model, arcface, system: PalmVeinBiometricSystem, photo: Path,
                     idx_to_class: dict, top_k: int = 5):
    emb_np = system._preprocess_to_embedding(photo)
    emb = torch.from_numpy(emb_np).unsqueeze(0)
    with torch.no_grad():
        logits = arcface.predict_logits(emb)
        scores, indices = torch.topk(logits.squeeze(0), k=min(top_k, logits.shape[1]))

    predictions = []
    for score, idx in zip(scores.tolist(), indices.tolist()):
        subject_id, hand = idx_to_class[idx]
        predictions.append({
            "subject_id": subject_id,
            "hand": hand,
            "identity": f"{subject_id}_{hand}",
            "cosine_similarity": float(score),
        })
    return predictions


def main() -> None:
    photos = collect_images(LIVE_ENROLL_DIR)
    if not photos:
        print(f"No images found in {LIVE_ENROLL_DIR}")
        return

    print(f"Model:  {CHECKPOINT_PRODUCTION}")
    print(f"Folder: {LIVE_ENROLL_DIR}")
    print(f"Photos: {len(photos)}")
    print(f"Gallery: 244 trained identities (subject x hand)\n")

    model, arcface, idx_to_class = load_classifier(CHECKPOINT_PRODUCTION)
    system = PalmVeinBiometricSystem(CHECKPOINT_PRODUCTION)

    print("=" * 70)
    print("DATASET IDENTITY PREDICTION (one photo at a time)")
    print("=" * 70)

    for i, photo in enumerate(photos, start=1):
        print(f"\nPhoto {i}/{len(photos)}: {photo.name}")
        try:
            predictions = predict_identity(model, arcface, system, photo, idx_to_class, top_k=5)
        except CaptureQualityError as e:
            print(f"  Prediction: REJECTED (quality gate)")
            print(f"  Reason:     {e}")
            continue
        except ValueError as e:
            print(f"  Prediction: ERROR")
            print(f"  Reason:     {e}")
            continue

        top = predictions[0]
        accepted = top["cosine_similarity"] >= DEFAULT_THRESHOLD
        verdict = "MATCH" if accepted else "below threshold"
        print(f"  Top-1:      {top['identity']}  (sim={top['cosine_similarity']:.4f}, {verdict})")
        print(f"  Threshold:  {DEFAULT_THRESHOLD:.4f}")
        print(f"  Top-5:")
        for rank, p in enumerate(predictions, start=1):
            print(f"    {rank}. {p['identity']:>12}  sim={p['cosine_similarity']:.4f}")


if __name__ == "__main__":
    main()
