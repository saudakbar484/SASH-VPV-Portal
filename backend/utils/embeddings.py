"""(De)serialise 512-d float32 palm-vein embeddings.

The trained model already L2-normalises its output (see palm_vein.model.py
line ~114), so per-sample embeddings stored as BLOBs are unit vectors. The
per-user template is the L2-normalised average of its samples.
"""
from __future__ import annotations

import base64

import numpy as np

from backend.settings import EMBEDDING_DIM


def embedding_to_bytes(emb: np.ndarray) -> bytes:
    arr = np.ascontiguousarray(np.asarray(emb, dtype=np.float32).reshape(-1))
    if arr.size != EMBEDDING_DIM:
        raise ValueError(f"expected {EMBEDDING_DIM}-d embedding, got size={arr.size}")
    return arr.tobytes()


def bytes_to_embedding(blob: bytes) -> np.ndarray:
    arr = np.frombuffer(blob, dtype=np.float32)
    if arr.size != EMBEDDING_DIM:
        raise ValueError(f"expected {EMBEDDING_DIM}-d embedding blob, got size={arr.size}")
    return arr.copy()


def embedding_to_b64(emb: np.ndarray) -> str:
    return base64.b64encode(embedding_to_bytes(emb)).decode("ascii")


def b64_to_embedding(s: str) -> np.ndarray:
    return bytes_to_embedding(base64.b64decode(s))


def average_and_normalise(embeddings: list[np.ndarray]) -> np.ndarray:
    if not embeddings:
        raise ValueError("Cannot average empty embeddings list")
    stack = np.stack([np.asarray(e, dtype=np.float32).reshape(-1) for e in embeddings])
    avg = stack.mean(axis=0)
    norm = float(np.linalg.norm(avg))
    return (avg / (norm + 1e-8)).astype(np.float32)
