"""
ArcFace (Additive Angular Margin) loss, Day 2 Task 5 / Part 6 of PROJECT_PLAN.md.

Implementation follows the widely-used community pattern for ArcFace (normalize
embeddings and per-class weight vectors to unit length, compute cosine
similarity as the logit, add an angular margin m to the target class's angle,
scale by s, then apply standard cross-entropy). This is implemented from
general understanding of the method, NOT copied from a specific verified
source file - if exact correspondence to the original paper's equations is
needed, verify independently. The numerical correctness of THIS
implementation was verified in this session via a synthetic-data training
test (see __main__ below): loss decreases and training accuracy approaches
100% on separable synthetic clusters, confirming gradients flow correctly
and the margin mechanism is doing something sensible - it does not confirm
the implementation exactly matches the original paper's formulation.

s=64.0, m=0.5 are commonly-cited default values in ArcFace community
implementations for face recognition; NOT yet tuned for this dataset's
~11-images/class regime (Day 2 Task 1 already flagged that ArcFace's
per-class weight vectors are noisier to estimate with fewer samples/class -
these defaults are a starting point, not a final choice).
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class ArcFaceLoss(nn.Module):
    def __init__(self, embed_dim: int, num_classes: int, s: float = 64.0, m: float = 0.5, label_smoothing: float = 0.0):
        super().__init__()
        self.s = s
        self.m = m
        self.label_smoothing = label_smoothing
        self.weight = nn.Parameter(torch.randn(num_classes, embed_dim))
        nn.init.xavier_uniform_(self.weight)
        self.eps = 1e-7

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # embeddings are assumed already L2-normalized (PalmVeinEmbeddingNet does this).
        normalized_weight = F.normalize(self.weight, p=2, dim=1)
        cosine = F.linear(embeddings, normalized_weight)  # (batch, num_classes)
        cosine = cosine.clamp(-1.0 + self.eps, 1.0 - self.eps)

        theta = torch.acos(cosine)
        target_logit = torch.cos(theta + self.m)

        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)

        output = one_hot * target_logit + (1.0 - one_hot) * cosine
        output = output * self.s
        return F.cross_entropy(output, labels, label_smoothing=self.label_smoothing)

    def predict_logits(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Plain (no-margin) cosine similarity to each class's weight vector -
        used for classification-accuracy reporting, matching how the model
        would actually be queried at inference (no margin is applied then)."""
        normalized_weight = F.normalize(self.weight, p=2, dim=1)
        return F.linear(embeddings, normalized_weight)


if __name__ == "__main__":
    # Numerical sanity check on synthetic, well-separated clusters: if the
    # loss doesn't decrease and accuracy doesn't rise here, the
    # implementation has a real bug - this is not a dataset-specific test.
    torch.manual_seed(0)
    embed_dim = 32
    num_classes = 10
    n_per_class = 20

    centers = F.normalize(torch.randn(num_classes, embed_dim), dim=1) * 3.0
    data, labels = [], []
    for c in range(num_classes):
        pts = centers[c] + 0.3 * torch.randn(n_per_class, embed_dim)
        data.append(pts)
        labels.append(torch.full((n_per_class,), c, dtype=torch.long))
    data = F.normalize(torch.cat(data, dim=0), dim=1)
    labels = torch.cat(labels, dim=0)

    arcface = ArcFaceLoss(embed_dim, num_classes, s=32.0, m=0.3)
    optimizer = torch.optim.Adam(arcface.parameters(), lr=0.05)

    for epoch in range(60):
        optimizer.zero_grad()
        loss = arcface(data, labels)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0 or epoch == 59:
            with torch.no_grad():
                cosine = F.linear(data, F.normalize(arcface.weight, dim=1))
                preds = cosine.argmax(dim=1)
                acc = (preds == labels).float().mean().item()
            print(f"epoch {epoch:3d}  loss={loss.item():.4f}  train_acc={acc:.3f}")
