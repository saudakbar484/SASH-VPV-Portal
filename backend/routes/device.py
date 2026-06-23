"""/api/device/* routes - lifecycle, status, USB diagnostics."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.device.singleton import (
    deinit_device,
    ensure_loaded,
    get_device,
    init_device,
    stream_age_seconds,
    stream_fps,
)
from backend.device.usb import XRTECH_PID, XRTECH_VID, enumerate_usb

router = APIRouter(prefix="/api/device", tags=["device"])


class LoadResponse(BaseModel):
    loaded: bool
    message: Optional[str] = None


class InitResponse(BaseModel):
    success: bool
    message: str = ""
    code: Optional[int] = None
    feat_size: Optional[int] = None
    img_size: Optional[str] = None
    usb_devices: list[dict[str, Any]] = []


class StatusResponse(BaseModel):
    loaded: bool
    connected: bool
    img_size: str = "480x640"
    feat_size: Optional[int] = None
    sdk_dir: str
    xrtech_visible_on_usb: bool


class UsbResponse(BaseModel):
    usb_devices: list[dict[str, Any]]
    xrtech_present: bool


class StreamStatusResponse(BaseModel):
    connected: bool
    fps: float
    last_frame_age_seconds: Optional[float] = None


@router.post("/load", response_model=LoadResponse)
def load() -> LoadResponse:
    ok = ensure_loaded()
    return LoadResponse(loaded=ok, message=None if ok else "DLL load failed")


@router.post("/init", response_model=InitResponse)
def init() -> InitResponse:
    result = init_device()
    return InitResponse(
        success=bool(result.get("success", False)),
        message=str(result.get("message", "")),
        code=result.get("code"),
        feat_size=result.get("feat_size"),
        img_size=result.get("img_size"),
        usb_devices=enumerate_usb(),
    )


@router.post("/deinit")
def deinit() -> dict[str, bool]:
    deinit_device()
    return {"success": True}


@router.post("/reconnect", response_model=InitResponse)
def reconnect() -> InitResponse:
    deinit_device()
    return init()


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    device = get_device()
    usb_devices = enumerate_usb()
    xrtech_visible = any(d.get("is_xrtech") for d in usb_devices)
    return StatusResponse(
        loaded=device._dll is not None,
        connected=device.is_connected(),
        img_size=f"{device.IMG_W}x{device.IMG_H}",
        feat_size=device._feat_size if device.is_connected() else None,
        sdk_dir=str(device.sdk_dir),
        xrtech_visible_on_usb=xrtech_visible,
    )


@router.get("/usb", response_model=UsbResponse)
def usb() -> UsbResponse:
    devices = enumerate_usb()
    return UsbResponse(
        usb_devices=devices,
        xrtech_present=any(d.get("is_xrtech") for d in devices),
    )


@router.get("/stream-status", response_model=StreamStatusResponse)
def stream_status() -> StreamStatusResponse:
    device = get_device()
    return StreamStatusResponse(
        connected=device.is_connected(),
        fps=stream_fps(),
        last_frame_age_seconds=stream_age_seconds(),
    )
