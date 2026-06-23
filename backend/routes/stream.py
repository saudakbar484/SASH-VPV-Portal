"""MJPEG stream, single-frame snapshot, raw frame, and capture-to-disk routes."""
from __future__ import annotations

import asyncio
import io
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.device.singleton import get_device, get_fresh_frame
from backend.settings import CAPTURES_DIR

# Imported after settings (paths configured by backend.settings import side effect).
from xrtech_device import XRTechDevice, frame_to_jpeg, save_frame_png  # noqa: E402

router = APIRouter(tags=["stream"])

MJPEG_BOUNDARY = "frame"
MJPEG_DEFAULT_FPS = 15
MJPEG_MAX_FPS = 25


class CaptureResponse(BaseModel):
    success: bool
    filename: str
    path: str
    timestamp: str
    width: int
    height: int
    bytes: int


def _blank_jpeg(message: str = "No signal") -> bytes:
    """Return a small placeholder JPEG when the sensor is not connected."""
    from PIL import Image, ImageDraw

    img = Image.new("L", (XRTechDevice.IMG_W, XRTechDevice.IMG_H), color=0)
    draw = ImageDraw.Draw(img)
    draw.text((20, XRTechDevice.IMG_H // 2 - 8), message, fill=255)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def _grab_jpeg() -> tuple[bool, bytes]:
    """Synchronous: pull one raw frame (auto-healed) and JPEG-encode it."""
    device = get_device()
    if not device.is_connected():
        return False, _blank_jpeg("Sensor not connected")
    raw = get_fresh_frame()
    if not raw:
        return False, _blank_jpeg("No frame")
    try:
        jpeg = frame_to_jpeg(raw, XRTechDevice.IMG_W, XRTechDevice.IMG_H)
        return True, jpeg
    except Exception as e:
        return False, _blank_jpeg(f"Encode error: {e}")


def _grab_raw() -> bytes | None:
    device = get_device()
    if not device.is_connected():
        return None
    return get_fresh_frame()


@router.get("/api/stream")
async def stream(fps: int = Query(MJPEG_DEFAULT_FPS, ge=1, le=MJPEG_MAX_FPS)) -> StreamingResponse:
    """MJPEG stream. Use as: <img src="/api/stream" />."""
    interval = 1.0 / fps

    def _mjpeg_chunk(jpeg: bytes) -> bytes:
        header = (
            f"--{MJPEG_BOUNDARY}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg)}\r\n\r\n"
        ).encode("ascii")
        return header + jpeg + b"\r\n"

    async def generator() -> AsyncIterator[bytes]:
        try:
            # Send a placeholder immediately so the browser <img> onLoad fires
            # even when the SDK is slow or contended.
            yield _mjpeg_chunk(_blank_jpeg("Connecting…"))
            while True:
                _ok, jpeg = await asyncio.to_thread(_grab_jpeg)
                yield _mjpeg_chunk(jpeg)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        generator(),
        media_type=f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/frame")
async def frame_snapshot() -> Response:
    """Single JPEG snapshot of the current sensor frame."""
    ok, jpeg = await asyncio.to_thread(_grab_jpeg)
    status_code = 200 if ok else 503
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/device/raw")
async def device_raw() -> Response:
    """Raw 480x640 grayscale bytes from the sensor (no encoding). Debug use."""
    raw = await asyncio.to_thread(_grab_raw)
    if raw is None:
        raise HTTPException(status_code=503, detail="Sensor not connected or no frame")
    return Response(
        content=raw,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Image-Width": str(XRTechDevice.IMG_W),
            "X-Image-Height": str(XRTechDevice.IMG_H),
            "X-Image-Format": "L8",
        },
    )


@router.post("/api/capture", response_model=CaptureResponse)
async def capture() -> CaptureResponse:
    """Capture a single frame and persist it as a PNG under data/users/_captures/."""
    device = get_device()
    if not device.is_connected():
        raise HTTPException(status_code=503, detail="Sensor not connected")

    raw = await asyncio.to_thread(get_fresh_frame)
    if not raw:
        raise HTTPException(status_code=503, detail="Failed to grab frame")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"capture_{timestamp}.png"
    out_path = CAPTURES_DIR / filename
    await asyncio.to_thread(save_frame_png, raw, out_path)

    return CaptureResponse(
        success=True,
        filename=filename,
        path=str(out_path),
        timestamp=timestamp,
        width=XRTechDevice.IMG_W,
        height=XRTechDevice.IMG_H,
        bytes=len(raw),
    )
