"""Lazy singleton for the PalmVeinBiometricSystem matcher.

First access loads torch + the production checkpoint (~3-5 s cold).
Subsequent calls are cheap.
"""
from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np

from backend.matcher.inference_device import configure_torch_runtime, resolve_inference_device
from backend.settings import CHECKPOINT_PRODUCTION, DEFAULT_THRESHOLD, INFERENCE_DEVICE
from xrtech_device import XRTechDevice  # noqa: E402

if TYPE_CHECKING:
    from palm_vein.deployment import PalmVeinBiometricSystem

logger = logging.getLogger(__name__)

_matcher: Optional["PalmVeinBiometricSystem"] = None
_device = None
_lock = Lock()


def reload_matcher() -> None:
    """Drop cached matcher so the next call loads the latest checkpoint."""
    global _matcher
    with _lock:
        _matcher = None
    logger.info("Matcher cache cleared — will reload on next embed request")


def get_matcher() -> "PalmVeinBiometricSystem":
    """Return the singleton; load on first call."""
    global _matcher, _device
    if _matcher is not None:
        return _matcher
    with _lock:
        if _matcher is None:
            configure_torch_runtime()
            from palm_vein.deployment import PalmVeinBiometricSystem

            _device = resolve_inference_device(INFERENCE_DEVICE)
            logger.info(
                "Loading PalmVeinBiometricSystem from %s on %s ...",
                CHECKPOINT_PRODUCTION.name,
                _device,
            )
            _matcher = PalmVeinBiometricSystem(
                CHECKPOINT_PRODUCTION,
                threshold=DEFAULT_THRESHOLD,
                device=_device,
            )
            logger.info("Matcher loaded (threshold=%s, device=%s)", DEFAULT_THRESHOLD, _device)
    return _matcher


def embed_image(image_path: Path) -> np.ndarray:
    """Run the model on one PNG and return its 512-d L2-normalised embedding."""
    matcher = get_matcher()
    return matcher._preprocess_to_embedding(image_path)


def embed_png_bytes(raw: bytes) -> np.ndarray:
    """Embed a capture buffer: PNG/JPEG bytes or raw L8 sensor frame."""
    matcher = get_matcher()
    arr = np.frombuffer(raw, dtype=np.uint8)
    gray = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        w, h = XRTechDevice.IMG_W, XRTechDevice.IMG_H
        expected = w * h
        if len(raw) >= expected:
            gray = np.frombuffer(raw[:expected], dtype=np.uint8).reshape(h, w)
        else:
            raise ValueError("Could not decode PNG frame from scanner")
    return matcher._preprocess_gray_to_embedding(gray)
