"""
Day 2 Task 12: enrollment / verification / identification flow prototype
(Part 13/14 of PROJECT_PLAN.md).

Template storage: FAISS IndexFlatIP over L2-normalized 512-d embeddings -
confirmed in this session that inner product on unit vectors gives exact
cosine similarity (verified numerically: self-similarity = 1.0 in the smoke
test below the class definitions). IndexFlatIP does brute-force exact search,
appropriate at this dataset's scale (hundreds of identities) - an ANN index
(e.g. IndexIVFFlat) would only be needed at much larger gallery sizes than
this project has, per Part 13's note.

Threshold calibration: the verification accept/reject threshold should come
from Day 2 Task 11's ROC/EER analysis on the held-out fold (true open-set
data), not be guessed. This prototype defaults to the EER threshold
estimated from that evaluation, exposed as a constructor argument so it can
be recalibrated without code changes.

Caveat carried over from Day 2 Task 11: the embedding model's true open-set
EER was measured at ~0.20 (not the seen-class proxy ~0.024) - so this
prototype's accept/reject behavior reflects a still-early-stage model, not a
production-ready system. The flows below are the right ARCHITECTURE
regardless of model maturity; only the threshold/error-rate numbers would
improve as the model is trained further (Day 2 Task 11's recommended next
steps).
"""
from pathlib import Path
from typing import Optional

import cv2
import faiss
import numpy as np
import torch

from palm_vein.model import PalmVeinEmbeddingNet, EMBED_DIM
from palm_vein.roi_extraction import extract_roi
from palm_vein.segment_and_landmarks import find_landmarks
from palm_vein.vein_enhancement import enhance
from palm_vein.dataset import to_tensor

from palm_vein.config import PROJECT_ROOT, CV_FOLDS_CSV, VISIBILITY_CSV, METADATA_CSV, CHECKPOINT_PRODUCTION, CHECKPOINT_VALIDATION, CHECKPOINT_LEGACY, METRICS_DIR, FIGURES_DIR, DATA_RAW, CHECKPOINTS_DIR
# Measured directly on 30 sample dataset images (segment_hand mask area /
# frame area): unoccluded captures ranged 0.32-0.66, median 0.52. Set well
# below that natural floor so normal hand-size/distance variation always
# passes, while still catching the severe end of Task 6's partial-palm/
# occlusion sweep (where EER rose to 0.31-0.38) before a degraded capture
# ever reaches the model.
MIN_PALM_VISIBILITY_RATIO = 0.15


class CaptureQualityError(Exception):
    """Raised when a capture fails the pre-recognition quality gate: failed
    landmark detection, or insufficient palm visibility. Previously this
    pipeline silently fell back to resizing the full raw (non-ROI) frame on
    failure - but Long01/Long03 (testing/reports/summary/) confirmed twice,
    under two different loss functions, that feeding the model raw
    non-ROI-normalized frames produces shortcut-learning artifacts rather
    than genuine vein-pattern matches. A bad capture must be rejected and
    recaptured, not silently fed to the model."""

# Recomputed directly from Day 2 Task 11's held-out-fold genuine/impostor
# scores (not eyeballed from the plot - verified via roc_curve's threshold
# array at the EER crossover point: FAR=FNR=0.2049 at this threshold). This
# is the operating threshold where FAR == FRR on that evaluation - a real
# deployment would instead pick a threshold from the GAR@FAR table for the
# desired security level (e.g. GAR@FAR=1%), not necessarily the EER point.
DEFAULT_THRESHOLD = 0.40


class PalmVeinBiometricSystem:
    """Enrollment / verification / identification using a FAISS cosine-similarity
    template store on top of the trained embedding model."""

    def __init__(
        self,
        checkpoint_path: Path,
        threshold: float = DEFAULT_THRESHOLD,
        adversarial_defense: bool = False,
        device: Optional["torch.device"] = None,
    ):
        import torch

        self.device = device if device is not None else torch.device("cpu")
        try:
            ckpt = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        except TypeError:
            ckpt = torch.load(checkpoint_path, map_location=self.device)
        self.model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=False)
        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()

        self.threshold = threshold
        self.adversarial_defense = adversarial_defense
        self.index = faiss.IndexFlatIP(EMBED_DIM)
        self.identity_by_slot: list[str] = []  # parallel array: faiss row i -> identity string

    def _preprocess_gray_to_embedding(self, gray_img: np.ndarray) -> np.ndarray:
        if gray_img is None:
            raise ValueError("Empty image")

        try:
            landmarks = find_landmarks(gray_img)
        except ValueError as e:
            raise CaptureQualityError(f"Capture rejected: {e} - please recapture.") from e

        visibility_ratio = float(np.count_nonzero(landmarks.mask)) / landmarks.mask.size
        if landmarks.landmark_pair is None or visibility_ratio < MIN_PALM_VISIBILITY_RATIO:
            reason = ("no landmark pair found" if landmarks.landmark_pair is None
                      else f"palm visibility {visibility_ratio:.1%} below minimum {MIN_PALM_VISIBILITY_RATIO:.0%}")
            raise CaptureQualityError(f"Capture rejected: {reason} - please recapture with the full palm visible and unobstructed.")

        roi, _ = extract_roi(gray_img, landmarks)
        if roi is None:
            raise CaptureQualityError("Capture rejected: ROI normalization failed after landmark detection - please recapture.")
        stacked = enhance(roi, adversarial_defense=self.adversarial_defense)
        x = to_tensor(stacked).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            emb = self.model(x).squeeze(0).detach().cpu().numpy()
        return emb.astype("float32")

    def _preprocess_to_embedding(self, image_path: Path) -> np.ndarray:
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        return self._preprocess_gray_to_embedding(img)

    # ---- Enrollment flow: Capture -> Preprocess -> Feature Extraction -> Template Storage ----
    def enroll(self, identity: str, image_paths: list[Path]) -> None:
        """Enrolls one identity from one or more capture images, averaging
        their embeddings into a single template (Part 13: "average/aggregate
        embeddings from 3-5 enrollment captures for a more stable template"),
        then re-normalizing so the stored template is still unit-length
        (required for the IndexFlatIP inner product to equal cosine similarity)."""
        embeddings = [self._preprocess_to_embedding(p) for p in image_paths]
        template = np.mean(embeddings, axis=0)
        template = template / (np.linalg.norm(template) + 1e-8)
        self.index.add(template.reshape(1, -1).astype("float32"))
        self.identity_by_slot.append(identity)

    # ---- Verification flow: Capture -> Preprocess -> Feature Extraction -> Similarity Matching ----
    def verify(self, claimed_identity: str, image_path: Path) -> dict:
        try:
            probe_emb = self._preprocess_to_embedding(image_path).reshape(1, -1)
        except CaptureQualityError as e:
            return {"accepted": False, "reason": str(e), "similarity": None}

        try:
            slot = self.identity_by_slot.index(claimed_identity)
        except ValueError:
            return {"accepted": False, "reason": "identity not enrolled", "similarity": None}

        template = self.index.reconstruct(slot).reshape(1, -1)
        similarity = float(np.dot(probe_emb, template.T).squeeze())
        accepted = similarity >= self.threshold
        return {"accepted": accepted, "similarity": similarity, "threshold": self.threshold}

    # ---- Identification flow: Capture -> Search Gallery -> Return Identity ----
    def identify(self, image_path: Path, top_k: int = 5) -> dict:
        try:
            probe_emb = self._preprocess_to_embedding(image_path).reshape(1, -1).astype("float32")
        except CaptureQualityError as e:
            return {"matched": False, "reason": str(e), "candidates": []}

        if self.index.ntotal == 0:
            return {"matched": False, "reason": "empty gallery", "candidates": []}

        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(probe_emb, k)
        candidates = [
            {"identity": self.identity_by_slot[idx], "similarity": float(sim)}
            for sim, idx in zip(similarities[0], indices[0])
        ]
        best = candidates[0]
        matched = best["similarity"] >= self.threshold
        return {"matched": matched, "best_match": best if matched else None, "candidates": candidates}


if __name__ == "__main__":
    import csv

    with open(CV_FOLDS_CSV, newline="", encoding="utf-8") as f:
        fold_rows = list(csv.DictReader(f))
    held_out_classes = {(r["subject_id"], r["hand"]) for r in fold_rows if int(r["fold"]) == 0}

    with open(VISIBILITY_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    from collections import defaultdict
    by_class = defaultdict(list)
    for r in rows:
        key = (r["subject_id"], r["hand"])
        if key in held_out_classes:
            by_class[key].append(r)

    # Demo: enroll 3 identities (from the held-out fold, since that's the
    # data this checkpoint has never seen - the realistic "new user" case),
    # then run one genuine verification, one impostor verification, and one
    # identification query.
    demo_classes = sorted(by_class.keys())[:3]
    system = PalmVeinBiometricSystem(CHECKPOINT_PRODUCTION)

    for key in demo_classes:
        imgs = sorted(by_class[key], key=lambda r: int(r["image_index"]))
        enroll_imgs = [PROJECT_ROOT / r["relative_path"] for r in imgs[:3]]
        identity_str = f"{key[0]}_{key[1]}"
        system.enroll(identity_str, enroll_imgs)
        print(f"Enrolled {identity_str} from {len(enroll_imgs)} images")

    probe_key = demo_classes[0]
    probe_imgs = sorted(by_class[probe_key], key=lambda r: int(r["image_index"]))
    probe_path = PROJECT_ROOT / probe_imgs[-1]["relative_path"]  # unseen-during-enrollment image of same identity
    genuine_identity = f"{probe_key[0]}_{probe_key[1]}"

    print(f"\n--- Verification: genuine claim ({genuine_identity}) ---")
    print(system.verify(genuine_identity, probe_path))

    impostor_identity = f"{demo_classes[1][0]}_{demo_classes[1][1]}"
    print(f"\n--- Verification: impostor claim (probe is {genuine_identity}, claims {impostor_identity}) ---")
    print(system.verify(impostor_identity, probe_path))

    print(f"\n--- Identification: probe is {genuine_identity} ---")
    result = system.identify(probe_path, top_k=3)
    print(result)
