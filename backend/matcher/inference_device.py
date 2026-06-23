"""PyTorch device selection and runtime tuning for palm inference."""
from __future__ import annotations

import logging
import os

import torch

logger = logging.getLogger(__name__)

_configured = False


def resolve_inference_device(preferred: str | None = None) -> torch.device:
    """Pick cuda / cpu from env INFERENCE_DEVICE or auto-detect."""
    choice = (preferred or os.environ.get("INFERENCE_DEVICE", "auto")).strip().lower()
    if choice == "cpu":
        return torch.device("cpu")
    if choice in ("cuda", "gpu"):
        if torch.cuda.is_available():
            return torch.device("cuda")
        logger.warning("INFERENCE_DEVICE=%s but CUDA unavailable — using CPU", choice)
        return torch.device("cpu")
    # auto
    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        logger.info("CUDA available — using GPU: %s", name)
        return torch.device("cuda")
    logger.info("CUDA not available — using CPU for palm inference")
    return torch.device("cpu")


def configure_torch_runtime() -> None:
    """Call once at process startup."""
    global _configured
    if _configured:
        return
    _configured = True
    try:
        torch.set_num_threads(max(1, int(os.environ.get("TORCH_NUM_THREADS", "4"))))
    except Exception:
        pass
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
