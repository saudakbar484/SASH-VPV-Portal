#!/usr/bin/env python3
"""Quick smoke test for XRTECH MagicVein Plus scanner."""
from __future__ import annotations

import atexit
import base64
import sys
from pathlib import Path

from xrtech_device import XRTechDevice, frame_to_jpeg, save_frame_png

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)


def main() -> int:
    dev = XRTechDevice()
    print(f"SDK dir: {dev.sdk_dir}")

    if not dev.load():
        print("FAIL: Could not load XRCommonVeinPlusAPI.dll")
        return 1

    result = dev.init()
    print("Init:", result)
    if not result.get("success"):
        return 1

    atexit.register(dev.deinit)

    raw = dev.get_frame()
    if raw:
        jpg_path = OUT / "test_frame.jpg"
        png_path = OUT / "test_frame.png"
        jpg_path.write_bytes(frame_to_jpeg(raw))
        save_frame_png(raw, png_path)
        print(f"Frame saved: {jpg_path} ({len(raw)} raw bytes)")
    else:
        print("WARN: No frame (hold palm over sensor and retry)")

    print("Capturing feature — hold palm steady over sensor...")
    feat, diag = dev.capture_feature(max_tries=30)
    print("Capture diagnostics:", diag)
    if feat:
        b64 = base64.b64encode(feat).decode()
        (OUT / "test_feature.b64").write_text(b64)
        print(f"Feature: {len(feat)} bytes -> output/test_feature.b64")
    else:
        print("WARN: Feature capture failed")

    dev.deinit()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
