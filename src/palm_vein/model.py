"""
EfficientNet-B0 + CBAM backbone with an embedding head (Part 7/8 of
PROJECT_PLAN.md, Day 2 Task 3).

Backbone: timm's efficientnet_b0, ImageNet-pretrained (confirmed working in
this environment - weights downloaded successfully from the HF Hub during
this session), used via features_only=True to get the 5 intermediate
feature maps. Confirmed feature map shapes for a 224x224 input (verified by
direct inspection, not assumed):
    stage0: (B, 16,  112,112)
    stage1: (B, 24,  56, 56)
    stage2: (B, 40,  28, 28)
    stage3: (B, 112, 14, 14)
    stage4: (B, 320, 7,  7)

IMPORTANT implementation note on CBAM placement: timm's features_only=True
mode runs the backbone's forward pass internally and exposes intermediate
activations as independent outputs - it does NOT let us splice CBAM back
into the backbone's own forward computation (that would require either
patching the backbone's internal blocks or hooking into it more invasively).
An earlier draft of this module computed a CBAM-refined version of an
intermediate stage's features but never actually used it anywhere in the
forward pass - dead computation that looked like it was doing something
when it wasn't. Fixed by applying CBAM to the last two stages' feature maps
(the higher-level, more semantic ones - where "which channel/region
matters" is most meaningful) and genuinely using BOTH in the final
embedding via multi-scale pooling (global-average-pool each, concatenate,
then project), rather than discarding one.

The final embedding head: concatenate the pooled CBAM-refined stage3 and
stage4 features, then a linear projection to EMBED_DIM, then L2-normalize -
this normalized embedding is what ArcFace (Day 2 Task 5) operates on, and
what cosine-similarity matching (Part 13) uses at deployment time.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm

EMBED_DIM = 512


class ChannelAttention(nn.Module):
    """SE-style channel attention: squeeze (avg+max pool) -> shared MLP -> sigmoid gate."""

    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        hidden = max(channels // reduction, 8)
        self.mlp = nn.Sequential(
            nn.Linear(channels, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.shape
        avg_pool = x.mean(dim=(2, 3))
        max_pool = x.amax(dim=(2, 3))
        gate = torch.sigmoid(self.mlp(avg_pool) + self.mlp(max_pool))
        self.last_gate = gate.detach()  # exposed for explainability (Day 2 Task 10)
        return x * gate.view(b, c, 1, 1)


class SpatialAttention(nn.Module):
    """Pools across channels (avg+max), conv to a 1-channel map, sigmoid gate."""

    def __init__(self, kernel_size: int = 7):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, padding=kernel_size // 2, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_pool = x.mean(dim=1, keepdim=True)
        max_pool = x.amax(dim=1, keepdim=True)
        gate = torch.sigmoid(self.conv(torch.cat([avg_pool, max_pool], dim=1)))
        self.last_gate = gate.detach()  # exposed for explainability (Day 2 Task 10)
        return x * gate


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 16, spatial_kernel: int = 7):
        super().__init__()
        self.channel_attention = ChannelAttention(channels, reduction)
        self.spatial_attention = SpatialAttention(spatial_kernel)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


class PalmVeinEmbeddingNet(nn.Module):
    def __init__(self, embed_dim: int = EMBED_DIM, pretrained: bool = True):
        super().__init__()
        self.backbone = timm.create_model("efficientnet_b0", pretrained=pretrained, features_only=True)
        channels = self.backbone.feature_info.channels()  # [16, 24, 40, 112, 320]

        # CBAM after the last two stages only (see module docstring).
        self.cbam_stage3 = CBAM(channels[3])
        self.cbam_stage4 = CBAM(channels[4])

        self.embedding = nn.Linear(channels[3] + channels[4], embed_dim)
        self.dropout = nn.Dropout(p=0.4)  # anti-overfitting (Part 12) - tuned further in Day2 Task6

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        f3 = self.cbam_stage3(features[3])
        f4 = self.cbam_stage4(features[4])
        if f4.requires_grad:  # only meaningful outside torch.no_grad() contexts
            f4.retain_grad()  # lets Grad-CAM (Day 2 Task 10) backprop into this feature map
        self.last_f4 = f4  # exposed for Grad-CAM/Score-CAM (Day 2 Task 10) - kept WITH grad, not detached
        pooled = torch.cat([f3.mean(dim=(2, 3)), f4.mean(dim=(2, 3))], dim=1)
        pooled = self.dropout(pooled)
        embedding = self.embedding(pooled)
        embedding = F.normalize(embedding, p=2, dim=1)
        return embedding


if __name__ == "__main__":
    model = PalmVeinEmbeddingNet(pretrained=True)
    model.eval()
    dummy = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        out = model(dummy)
    print("embedding shape:", out.shape)
    print("embedding L2 norms (should be ~1.0 each):", out.norm(dim=1))
    n_params = sum(p.numel() for p in model.parameters())
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"total params: {n_params:,}  trainable: {n_trainable:,}")
