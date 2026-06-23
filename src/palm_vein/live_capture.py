"""
Live capture GUI for the XRTECH MagicVein Plus scanner.

Opens a window with the live NIR vein-mask preview and a Capture button.
On capture: saves the frame as PNG into tests/live/captures/, then runs
the production model's 244-class identity prediction and prints the result
to the terminal.
"""
from __future__ import annotations

import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from tkinter import ttk

import torch
from PIL import Image, ImageTk

from palm_vein.arcface_loss import ArcFaceLoss
from palm_vein.config import (
    CHECKPOINT_PRODUCTION,
    LIVE_CAPTURES_DIR,
    XRTECH_DIR,
    XRTECH_SDK_DIR,
)
from palm_vein.deployment import (
    DEFAULT_THRESHOLD,
    CaptureQualityError,
    PalmVeinBiometricSystem,
)
from palm_vein.model import EMBED_DIM, PalmVeinEmbeddingNet

if str(XRTECH_DIR) not in sys.path:
    sys.path.insert(0, str(XRTECH_DIR))

from xrtech_device import XRTechDevice, save_frame_png  # noqa: E402

PREVIEW_W, PREVIEW_H = 360, 480
FRAME_INTERVAL_MS = 33


def load_classifier(checkpoint_path: Path):
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    class_to_idx = ckpt["class_to_idx"]
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    model = PalmVeinEmbeddingNet(embed_dim=EMBED_DIM, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    arcface = ArcFaceLoss(EMBED_DIM, len(class_to_idx))
    arcface.load_state_dict(ckpt["arcface_state_dict"])
    arcface.eval()
    return model, arcface, idx_to_class


def predict_identity(system: PalmVeinBiometricSystem, arcface, idx_to_class, image_path: Path, top_k: int = 5):
    emb_np = system._preprocess_to_embedding(image_path)
    emb = torch.from_numpy(emb_np).unsqueeze(0)
    with torch.no_grad():
        logits = arcface.predict_logits(emb)
        scores, indices = torch.topk(logits.squeeze(0), k=min(top_k, logits.shape[1]))
    return [
        {
            "identity": f"{idx_to_class[idx][0]}_{idx_to_class[idx][1]}",
            "similarity": float(score),
        }
        for score, idx in zip(scores.tolist(), indices.tolist())
    ]


class LiveCaptureApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("XRTECH Palm Vein Live Capture")
        self.root.geometry(f"{PREVIEW_W + 40}x{PREVIEW_H + 160}")
        self.stop_event = Event()
        self.last_raw_frame: bytes | None = None

        self.device = XRTechDevice(XRTECH_SDK_DIR)
        if not self.device.load():
            self._fatal("Failed to load XRCommonVeinPlusAPI.dll. Check SDK path.")
            return
        init_result = self.device.init()
        if not init_result.get("success"):
            self._fatal(f"Sensor init failed: {init_result.get('message')}")
            return

        print("Loading production model...")
        self.bio_system = PalmVeinBiometricSystem(CHECKPOINT_PRODUCTION)
        self.embed_model, self.arcface, self.idx_to_class = load_classifier(CHECKPOINT_PRODUCTION)
        print(f"Model loaded. Gallery: {len(self.idx_to_class)} identities.\n")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.preview_thread = Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(main, background="black")
        self.preview_label.pack()

        self.status_var = tk.StringVar(value="Hold palm 3-8 cm above the sensor")
        ttk.Label(main, textvariable=self.status_var, font=("Segoe UI", 10)).pack(pady=(8, 4))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=4)
        self.capture_btn = ttk.Button(btn_frame, text="Capture & Predict", command=self._on_capture)
        self.capture_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Quit", command=self._on_close).pack(side=tk.LEFT, padx=4)

        self.last_pred_var = tk.StringVar(value="No capture yet.")
        ttk.Label(main, textvariable=self.last_pred_var, font=("Segoe UI", 10, "bold"),
                  foreground="#0a5").pack(pady=(8, 0))

    def _preview_loop(self):
        while not self.stop_event.is_set():
            raw = self.device.get_frame()
            if raw:
                self.last_raw_frame = raw
                try:
                    img = Image.frombytes("L", (XRTechDevice.IMG_W, XRTechDevice.IMG_H),
                                          raw[:XRTechDevice.IMG_BYTES])
                    if img.getextrema()[1] <= 1:
                        img = img.point(lambda v: 255 if v else 0)
                    img = img.resize((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.root.after(0, self._update_preview, photo)
                except Exception as e:
                    print(f"[preview] {e}")
            time.sleep(FRAME_INTERVAL_MS / 1000.0)

    def _update_preview(self, photo: ImageTk.PhotoImage):
        self.preview_label.configure(image=photo)
        self.preview_label.image = photo

    def _on_capture(self):
        if not self.last_raw_frame:
            self.status_var.set("No live frame yet — wait a moment and retry.")
            return
        self.capture_btn.configure(state=tk.DISABLED)
        self.status_var.set("Capturing & predicting...")
        Thread(target=self._capture_and_predict,
               args=(self.last_raw_frame,), daemon=True).start()

    def _capture_and_predict(self, raw: bytes):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        out_path = LIVE_CAPTURES_DIR / f"capture_{timestamp}.png"
        LIVE_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        save_frame_png(raw, out_path)

        print("=" * 60)
        print(f"Captured: {out_path.name}")
        try:
            predictions = predict_identity(self.bio_system, self.arcface,
                                           self.idx_to_class, out_path, top_k=5)
        except CaptureQualityError as e:
            print(f"  Prediction: REJECTED ({e})")
            self.root.after(0, self._post_capture, "REJECTED — capture quality too low.", False)
            return
        except Exception as e:
            print(f"  Prediction: ERROR ({e})")
            self.root.after(0, self._post_capture, f"Error: {e}", False)
            return

        top = predictions[0]
        accepted = top["similarity"] >= DEFAULT_THRESHOLD
        verdict = "MATCH" if accepted else "below threshold"
        print(f"  Top-1:      {top['identity']} (sim={top['similarity']:.4f}, {verdict})")
        print(f"  Threshold:  {DEFAULT_THRESHOLD:.4f}")
        print(f"  Top-5:")
        for rank, p in enumerate(predictions, start=1):
            print(f"    {rank}. {p['identity']:>12}  sim={p['similarity']:.4f}")
        print("=" * 60)

        msg = f"Top-1: {top['identity']}  sim={top['similarity']:.4f}  ({verdict})"
        self.root.after(0, self._post_capture, msg, accepted)

    def _post_capture(self, message: str, ok: bool):
        self.last_pred_var.set(message)
        self.status_var.set("Ready — capture again or quit.")
        self.capture_btn.configure(state=tk.NORMAL)

    def _on_close(self):
        self.stop_event.set()
        try:
            self.device.deinit()
        except Exception:
            pass
        self.root.destroy()

    def _fatal(self, msg: str):
        print(f"FATAL: {msg}")
        try:
            self.device.deinit()
        except Exception:
            pass
        self.root.destroy()


def main():
    LIVE_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = LiveCaptureApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
