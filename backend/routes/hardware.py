"""/api/hardware/* - LED, volume, sleep, palm distance, and device info.

Wraps `XR_Vein_SetRgbState`, `XR_Vein_SetVolume`, `XR_Vein_SetSleepMode`,
`XR_Vein_GetPalmDist`, `XR_Vein_PlayWav`, `XR_Vein_GetSerialNum`, and
`XR_Vein_GetFwVersion` from the XRTECH SDK so the frontend can drive the
sensor's status LED, beeper, and read identifiers without touching ctypes.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.device.singleton import (
    cached_fw_version,
    cached_sdk_version,
    cached_serial,
    get_device,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hardware", tags=["hardware"])

# A handful of LED presets exposed by name so the frontend can use semantic
# colours ("success"/"error"/...) without knowing the raw RGB tuple. The
# tri-colour LED is documented as on/off per channel - we keep the values at
# 0 or 1 to match the SDK's effective range.
LED_PRESETS: dict[str, tuple[int, int, int]] = {
    "off":     (0, 0, 0),
    "red":     (1, 0, 0),
    "green":   (0, 1, 0),
    "blue":    (0, 0, 1),
    "yellow":  (1, 1, 0),
    "magenta": (1, 0, 1),
    "cyan":    (0, 1, 1),
    "white":   (1, 1, 1),
    # Semantic aliases for typical UI states.
    "idle":    (0, 0, 1),
    "success": (0, 1, 0),
    "warn":    (1, 1, 0),
    "error":   (1, 0, 0),
}


# --- Request / response models ---------------------------------------------


class LedRgbRequest(BaseModel):
    r: int = Field(..., ge=0, le=255)
    g: int = Field(..., ge=0, le=255)
    b: int = Field(..., ge=0, le=255)


class LedPresetRequest(BaseModel):
    preset: Literal[
        "off", "red", "green", "blue", "yellow", "magenta", "cyan", "white",
        "idle", "success", "warn", "error",
    ]


class LedResponse(BaseModel):
    success: bool
    r: int
    g: int
    b: int
    preset: Optional[str] = None
    message: Optional[str] = None


class VolumeRequest(BaseModel):
    # 0-100 percent from the UI; we map to the SDK's 0-31 hardware range.
    level: int = Field(..., ge=0, le=100)


class VolumeResponse(BaseModel):
    success: bool
    level_percent: int
    hw_level: int


class SleepRequest(BaseModel):
    enabled: bool


class SimpleSuccessResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class PlayWavRequest(BaseModel):
    sound_idx: int = Field(..., ge=0, le=255)


class PalmDistResponse(BaseModel):
    distance_mm: Optional[int]
    in_range: bool


class HardwareInfoResponse(BaseModel):
    connected: bool
    serial: Optional[str] = None
    fw_version: Optional[str] = None
    sdk_version: Optional[str] = None


# --- Helpers ---------------------------------------------------------------


def _require_connected():
    device = get_device()
    if not device.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Sensor not connected. Call POST /api/device/init first.",
        )
    return device


def _percent_to_hw_volume(percent: int) -> int:
    """Map 0-100 UI percent to the SDK's 0-31 hardware range."""
    pct = max(0, min(100, percent))
    return round(pct * 31 / 100)


# --- LED -------------------------------------------------------------------


@router.post("/led", response_model=LedResponse)
def set_led(body: LedRgbRequest) -> LedResponse:
    """Drive the tri-colour LED directly with r/g/b channel values."""
    device = _require_connected()
    ok = device.set_rgb(body.r, body.g, body.b)
    if not ok:
        raise HTTPException(status_code=500, detail="XR_Vein_SetRgbState failed")
    return LedResponse(success=True, r=body.r, g=body.g, b=body.b)


@router.post("/led/preset", response_model=LedResponse)
def set_led_preset(body: LedPresetRequest) -> LedResponse:
    """Apply a semantic LED preset (off / red / green / success / error / ...)."""
    device = _require_connected()
    rgb = LED_PRESETS[body.preset]
    ok = device.set_rgb(*rgb)
    if not ok:
        raise HTTPException(status_code=500, detail="XR_Vein_SetRgbState failed")
    return LedResponse(success=True, r=rgb[0], g=rgb[1], b=rgb[2], preset=body.preset)


@router.get("/led/presets", response_model=dict[str, tuple[int, int, int]])
def list_led_presets() -> dict[str, tuple[int, int, int]]:
    """Return the catalogue of available LED presets."""
    return LED_PRESETS


# --- Volume ----------------------------------------------------------------


@router.post("/volume", response_model=VolumeResponse)
def set_volume(body: VolumeRequest) -> VolumeResponse:
    """Set speaker volume in 0-100% (mapped to the SDK's 0-31 range).
    Only supported by some hardware revisions; failures will surface as 500."""
    device = _require_connected()
    hw = _percent_to_hw_volume(body.level)
    ok = device.set_volume(hw)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail="XR_Vein_SetVolume failed (module may not support audio)",
        )
    return VolumeResponse(success=True, level_percent=body.level, hw_level=hw)


# --- Sleep -----------------------------------------------------------------


@router.post("/sleep", response_model=SimpleSuccessResponse)
def set_sleep(body: SleepRequest) -> SimpleSuccessResponse:
    """Toggle the sensor's low-power sleep mode.

    In sleep mode the IR LEDs are off and the on-device algorithm is paused;
    `/api/frame` and `/api/stream` will return no-frame placeholders until
    the sensor is woken back up.
    """
    device = _require_connected()
    ok = device.set_sleep_mode(body.enabled)
    if not ok:
        raise HTTPException(status_code=500, detail="XR_Vein_SetSleepMode failed")
    return SimpleSuccessResponse(
        success=True,
        message="Sleep mode " + ("entered" if body.enabled else "exited"),
    )


# --- Audio cue -------------------------------------------------------------


@router.post("/play-wav", response_model=SimpleSuccessResponse)
def play_wav(body: PlayWavRequest) -> SimpleSuccessResponse:
    """Play a built-in audio cue by index (module-dependent)."""
    device = _require_connected()
    ok = device.play_wav(body.sound_idx)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail="XR_Vein_PlayWav failed (module may not support audio)",
        )
    return SimpleSuccessResponse(success=True)


# --- Palm distance (telemetry for the live preview) ------------------------


@router.get("/palm-distance", response_model=PalmDistResponse)
def palm_distance() -> PalmDistResponse:
    """Read the live palm-to-sensor distance in millimetres.

    The sensor's sweet spot is roughly 30-80 mm; distances beyond 400 mm are
    documented by the SDK as inaccurate.
    """
    device = _require_connected()
    dist = device.get_palm_distance_mm()
    in_range = dist is not None and 30 <= dist <= 120
    return PalmDistResponse(distance_mm=dist, in_range=in_range)


# --- Identifying info ------------------------------------------------------


@router.get("/info", response_model=HardwareInfoResponse)
def hardware_info() -> HardwareInfoResponse:
    """Return the serial number, firmware version, and SDK version.

    These values are cached at device init time because the XRTECH SDK
    occasionally returns garbled bytes for GetSerial / GetFwVersion after
    extended use - so calling them once during a fresh init gives us
    stable, accurate identifiers for the lifetime of the connection.
    """
    device = get_device()
    if not device.is_connected():
        return HardwareInfoResponse(connected=False)
    return HardwareInfoResponse(
        connected=True,
        serial=cached_serial(),
        fw_version=cached_fw_version(),
        sdk_version=cached_sdk_version(),
    )
