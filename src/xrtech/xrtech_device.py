#!/usr/bin/env python3
"""
Standalone XRTECH MagicVein Plus USB scanner wrapper.
Uses XRCommonVeinPlusAPI.dll v3.1.3 via ctypes (Windows x64).
"""
from __future__ import annotations

import ctypes
import io
import os
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Tuple

XR_PALM_FEATURE_SIZE = 560
XR_VEIN_THRESH = 0.95

PV_TIP_CAP_SUCCESS = 20
PV_TIP_ENROLL_FINISH = 100

CAP_TIP_MESSAGES = {
    1: "Place your palm on the sensor",
    2: "Move your palm farther away",
    3: "Move your palm closer",
    4: "Invalid lighting / brightness",
    5: "Keep your palm steady",
    6: "Keep your palm facing the correct direction",
    7: "Move your palm down",
    8: "Move your palm up",
    9: "Move your palm left",
    10: "Move your palm right",
    20: "Capture successful",
    100: "Enrollment finished",
}

# Default SDK path relative to this file
KIT_DIR = Path(__file__).parent.resolve()
DEFAULT_SDK_DIR = KIT_DIR / "sdk" / "XRCommonVeinPlus_V3.1.3_t113s" / "Library file" / "win_x64"


class XRTechDevice:
    """Wraps XRCommonVeinPlusAPI.dll via ctypes."""

    IMG_W = 480
    IMG_H = 640
    IMG_BYTES = IMG_W * IMG_H
    BUFFER_BYTES = 600 * 800

    def __init__(self, sdk_dir: str | Path | None = None):
        self.sdk_dir = Path(sdk_dir) if sdk_dir else DEFAULT_SDK_DIR
        self._dll: Optional[Any] = None
        self._ctx: Optional[ctypes.c_void_p] = None
        self._feat_size: int = XR_PALM_FEATURE_SIZE
        self._connected = False
        self._lock = Lock()
        self._setup_dll_path()

    def _setup_dll_path(self) -> None:
        os.environ["PATH"] = str(self.sdk_dir) + os.pathsep + os.environ.get("PATH", "")
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetDllDirectoryW(str(self.sdk_dir))

    def load(self) -> bool:
        try:
            dll_path = str(self.sdk_dir / "XRCommonVeinPlusAPI.dll")
            self._dll = ctypes.CDLL(dll_path)
            self._bind_signatures()
            return True
        except Exception as e:
            print(f"[XRTech] DLL load failed: {e}")
            return False

    def _bind_signatures(self) -> None:
        d = self._dll
        VOIDP = ctypes.c_void_p
        INTP = ctypes.POINTER(ctypes.c_int)
        INT32P = ctypes.POINTER(ctypes.c_int32)
        UBP = ctypes.POINTER(ctypes.c_ubyte)
        CHARP = ctypes.c_char_p
        FP = ctypes.POINTER(ctypes.c_float)

        d.XR_Vein_Init.argtypes = [ctypes.POINTER(VOIDP)]
        d.XR_Vein_Init.restype = ctypes.c_int
        d.XR_Vein_DeInit.argtypes = [VOIDP]
        d.XR_Vein_DeInit.restype = ctypes.c_int
        d.XR_Vein_GetDevCnt.argtypes = [VOIDP, INTP]
        d.XR_Vein_GetDevCnt.restype = ctypes.c_int
        d.XR_Vein_OpenDev.argtypes = [VOIDP, ctypes.c_int]
        d.XR_Vein_OpenDev.restype = ctypes.c_int
        d.XR_Vein_CloseDev.argtypes = [VOIDP]
        d.XR_Vein_CloseDev.restype = ctypes.c_int
        d.XR_Vein_GetFeatSize.argtypes = [VOIDP, INTP]
        d.XR_Vein_GetFeatSize.restype = ctypes.c_int
        d.XR_Vein_GetSrcImgSize.argtypes = [VOIDP, INTP, INTP, INTP]
        d.XR_Vein_GetSrcImgSize.restype = ctypes.c_int
        d.XR_Vein_GetStdVeinImage.argtypes = [VOIDP, UBP, ctypes.c_int32]
        d.XR_Vein_GetStdVeinImage.restype = ctypes.c_int
        d.XR_Vein_CapRecgFeat.argtypes = [VOIDP, UBP, INTP, INTP]
        d.XR_Vein_CapRecgFeat.restype = ctypes.c_int
        d.XR_Vein_StartEnrollPalm.argtypes = [VOIDP]
        d.XR_Vein_StartEnrollPalm.restype = ctypes.c_int
        d.XR_Vein_GetEnrollState.argtypes = [VOIDP, INTP, INTP]
        d.XR_Vein_GetEnrollState.restype = ctypes.c_int
        d.XR_Vein_FinishEnroll.argtypes = [VOIDP, UBP, INTP, UBP, INTP]
        d.XR_Vein_FinishEnroll.restype = ctypes.c_int
        d.XR_Vein_CalcFeatureDist.argtypes = [UBP, ctypes.c_int32, UBP, ctypes.c_int32, FP]
        d.XR_Vein_CalcFeatureDist.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_CheckFeat"):
            d.XR_Vein_CheckFeat.argtypes = [UBP, ctypes.c_int32]
            d.XR_Vein_CheckFeat.restype = ctypes.c_int

        # Hardware-control bindings (correct per xr_vein_api.h - the previous
        # SetRgbState binding was a 2-arg int which doesn't match the SDK's
        # actual 4-arg uint8_t signature).
        if hasattr(d, "XR_Vein_SetRgbState"):
            d.XR_Vein_SetRgbState.argtypes = [
                VOIDP, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
            ]
            d.XR_Vein_SetRgbState.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_SetVolume"):
            d.XR_Vein_SetVolume.argtypes = [VOIDP, ctypes.c_uint8]
            d.XR_Vein_SetVolume.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_SetSleepMode"):
            d.XR_Vein_SetSleepMode.argtypes = [VOIDP, ctypes.c_uint8]
            d.XR_Vein_SetSleepMode.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_GetPalmDist"):
            d.XR_Vein_GetPalmDist.argtypes = [VOIDP, INT32P]
            d.XR_Vein_GetPalmDist.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_PlayWav"):
            d.XR_Vein_PlayWav.argtypes = [VOIDP, ctypes.c_uint8]
            d.XR_Vein_PlayWav.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_GetSerialNum"):
            d.XR_Vein_GetSerialNum.argtypes = [VOIDP, UBP, INT32P]
            d.XR_Vein_GetSerialNum.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_GetFwVersion"):
            d.XR_Vein_GetFwVersion.argtypes = [VOIDP, CHARP, INT32P]
            d.XR_Vein_GetFwVersion.restype = ctypes.c_int
        if hasattr(d, "XR_Vein_GetVersion"):
            d.XR_Vein_GetVersion.argtypes = [CHARP, INT32P]
            d.XR_Vein_GetVersion.restype = ctypes.c_int

    def init(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"success": False, "message": ""}
        if not self._dll:
            result["message"] = "DLL not loaded"
            return result
        if self._connected:
            self.deinit()
        try:
            ctx = ctypes.c_void_p(0)
            rc = self._dll.XR_Vein_Init(ctypes.byref(ctx))
            if rc != 0 or not ctx.value:
                result.update(success=False, code=rc, message=f"XR_Vein_Init failed ({rc})")
                return result
            self._ctx = ctx

            cnt = ctypes.c_int(0)
            rc = self._dll.XR_Vein_GetDevCnt(self._ctx, ctypes.byref(cnt))
            if rc != 0 or cnt.value <= 0:
                self._dll.XR_Vein_DeInit(self._ctx)
                self._ctx = None
                result.update(success=False, code=rc,
                              message="No scanner detected. Check USB and Zadig WinUSB driver.")
                return result

            rc = self._dll.XR_Vein_OpenDev(self._ctx, 0)
            if rc != 0:
                self._dll.XR_Vein_DeInit(self._ctx)
                self._ctx = None
                result.update(success=False, code=rc, message=f"XR_Vein_OpenDev failed ({rc})")
                return result

            fs = ctypes.c_int(0)
            self._dll.XR_Vein_GetFeatSize(self._ctx, ctypes.byref(fs))
            self._feat_size = fs.value if fs.value > 0 else XR_PALM_FEATURE_SIZE

            self._connected = True
            result.update(success=True, message="Scanner connected",
                          feat_size=self._feat_size, img_size=f"{self.IMG_W}x{self.IMG_H}")
            return result
        except Exception as e:
            result["message"] = str(e)
            return result

    def deinit(self) -> None:
        if self._dll and self._ctx is not None:
            try:
                self._dll.XR_Vein_CloseDev(self._ctx)
            except Exception:
                pass
            try:
                self._dll.XR_Vein_DeInit(self._ctx)
            except Exception:
                pass
        self._ctx = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self._ctx is not None

    def get_frame(self) -> Optional[bytes]:
        if not self.is_connected():
            return None
        with self._lock:
            buf = (ctypes.c_ubyte * self.BUFFER_BYTES)()
            rc = self._dll.XR_Vein_GetStdVeinImage(
                self._ctx, buf, ctypes.c_int32(self.BUFFER_BYTES)
            )
            if rc != 0:
                return None
            return bytes(buf[: self.IMG_BYTES])

    def capture_feature(self, max_tries: int = 20, retry_delay: float = 0.05
                        ) -> Tuple[Optional[bytes], Dict[str, Any]]:
        if not self.is_connected():
            return None, {"reason": "not_connected"}
        with self._lock:
            last_rc, last_tip = None, None
            for attempt in range(1, max_tries + 1):
                feat = (ctypes.c_ubyte * self._feat_size)()
                got = ctypes.c_int(self._feat_size)
                cap_tip = ctypes.c_int(0)
                rc = self._dll.XR_Vein_CapRecgFeat(
                    self._ctx, feat, ctypes.byref(got), ctypes.byref(cap_tip))
                last_rc, last_tip = rc, cap_tip.value
                if rc == 0 and got.value > 0:
                    return bytes(feat[:got.value]), {
                        "rc": rc, "cap_tip": cap_tip.value,
                        "message": CAP_TIP_MESSAGES.get(cap_tip.value, ""),
                        "attempts": attempt,
                    }
                time.sleep(retry_delay)
            return None, {
                "rc": last_rc, "cap_tip": last_tip,
                "message": CAP_TIP_MESSAGES.get(last_tip or 0, ""),
                "attempts": max_tries,
            }

    def calc_dist(self, feat_a: bytes, feat_b: bytes) -> Optional[float]:
        if not self._dll or not feat_a or not feat_b:
            return None
        a = (ctypes.c_ubyte * len(feat_a)).from_buffer_copy(feat_a)
        b = (ctypes.c_ubyte * len(feat_b)).from_buffer_copy(feat_b)
        dist = ctypes.c_float()
        rc = self._dll.XR_Vein_CalcFeatureDist(
            a, ctypes.c_int32(len(feat_a)), b, ctypes.c_int32(len(feat_b)), ctypes.byref(dist))
        return float(dist.value) if rc == 0 else None

    def match(self, probe: bytes, template: bytes) -> Tuple[bool, Optional[float]]:
        dist = self.calc_dist(probe, template)
        if dist is None:
            return False, None
        return dist < XR_VEIN_THRESH, dist

    def start_enroll(self) -> bool:
        if not self.is_connected():
            return False
        return self._dll.XR_Vein_StartEnrollPalm(self._ctx) == 0

    def get_enroll_status(self) -> Dict[str, Any]:
        if not self.is_connected():
            return {"state": -1}
        state, cap_tip = ctypes.c_int(), ctypes.c_int()
        rc = self._dll.XR_Vein_GetEnrollState(
            self._ctx, ctypes.byref(state), ctypes.byref(cap_tip))
        if rc == 0:
            return {
                "state": state.value,
                "cap_tip": cap_tip.value,
                "message": CAP_TIP_MESSAGES.get(cap_tip.value, ""),
            }
        return {"state": -1}

    def finish_enroll(self) -> Optional[bytes]:
        if not self.is_connected():
            return None
        img_len = ctypes.c_int(0)
        feat = (ctypes.c_ubyte * self._feat_size)()
        feat_len = ctypes.c_int(self._feat_size)
        rc = self._dll.XR_Vein_FinishEnroll(
            self._ctx, None, ctypes.byref(img_len), feat, ctypes.byref(feat_len))
        if rc == 0 and feat_len.value > 0:
            return bytes(feat[:feat_len.value])
        return None

    def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set the tri-color LED. Per the SDK, each channel is on/off (any
        non-zero value lights that channel); values are clamped to uint8."""
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_SetRgbState"):
            return False
        return self._dll.XR_Vein_SetRgbState(
            self._ctx,
            ctypes.c_uint8(max(0, min(255, int(r)))),
            ctypes.c_uint8(max(0, min(255, int(g)))),
            ctypes.c_uint8(max(0, min(255, int(b)))),
        ) == 0

    def set_volume(self, level: int) -> bool:
        """Set speaker volume. Hardware accepts 0-31; values outside are clamped."""
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_SetVolume"):
            return False
        level = max(0, min(31, int(level)))
        return self._dll.XR_Vein_SetVolume(self._ctx, ctypes.c_uint8(level)) == 0

    def set_sleep_mode(self, enabled: bool) -> bool:
        """Enter/exit low-power sleep mode (IR LEDs off + algorithm paused)."""
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_SetSleepMode"):
            return False
        return self._dll.XR_Vein_SetSleepMode(self._ctx, ctypes.c_uint8(1 if enabled else 0)) == 0

    def play_wav(self, sound_idx: int) -> bool:
        """Play a built-in audio cue (module-dependent)."""
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_PlayWav"):
            return False
        return self._dll.XR_Vein_PlayWav(
            self._ctx, ctypes.c_uint8(max(0, min(255, int(sound_idx))))
        ) == 0

    def get_palm_distance_mm(self) -> Optional[int]:
        """Return live palm-to-sensor distance in millimeters, or None on failure.
        SDK note: distances over ~400 mm become inaccurate."""
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_GetPalmDist"):
            return None
        dist = ctypes.c_int32(0)
        rc = self._dll.XR_Vein_GetPalmDist(self._ctx, ctypes.byref(dist))
        return int(dist.value) if rc == 0 else None

    def get_serial_number(self) -> Optional[str]:
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_GetSerialNum"):
            return None
        buf_size = ctypes.c_int32(64)
        buf = (ctypes.c_ubyte * 64)()
        rc = self._dll.XR_Vein_GetSerialNum(self._ctx, buf, ctypes.byref(buf_size))
        if rc != 0 or buf_size.value <= 0:
            return None
        return bytes(buf[: buf_size.value]).decode("ascii", errors="replace").strip("\x00").strip()

    def get_fw_version(self) -> Optional[str]:
        if not self.is_connected() or not hasattr(self._dll, "XR_Vein_GetFwVersion"):
            return None
        buf_size = ctypes.c_int32(64)
        buf = ctypes.create_string_buffer(64)
        rc = self._dll.XR_Vein_GetFwVersion(self._ctx, buf, ctypes.byref(buf_size))
        if rc != 0 or buf_size.value <= 0:
            return None
        return buf.value[: buf_size.value].decode("ascii", errors="replace").strip()

    def get_sdk_version(self) -> Optional[str]:
        """Get the SDK version string (does not require an open device)."""
        if not self._dll or not hasattr(self._dll, "XR_Vein_GetVersion"):
            return None
        buf_size = ctypes.c_int32(64)
        buf = ctypes.create_string_buffer(64)
        rc = self._dll.XR_Vein_GetVersion(buf, ctypes.byref(buf_size))
        if rc != 0 or buf_size.value <= 0:
            return None
        return buf.value[: buf_size.value].decode("ascii", errors="replace").strip()

    def check_feature(self, feat: bytes) -> Optional[Dict[str, Any]]:
        if not self._dll or not hasattr(self._dll, "XR_Vein_CheckFeat") or not feat:
            return None
        feat_ptr = (ctypes.c_ubyte * len(feat)).from_buffer_copy(feat)
        rc = self._dll.XR_Vein_CheckFeat(feat_ptr, ctypes.c_int32(len(feat)))
        return {"valid": rc == 0, "check_code": rc}


def frame_to_jpeg(raw: bytes, w: int = 480, h: int = 640) -> bytes:
    from PIL import Image, ImageFilter
    img = Image.frombytes("L", (w, h), raw[: w * h])
    if img.getextrema()[1] <= 1:
        img = img.point(lambda v: 255 if v else 0)
        img = img.filter(ImageFilter.MaxFilter(3))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def save_frame_png(raw: bytes, path: str | Path, w: int = 480, h: int = 640) -> None:
    from PIL import Image
    img = Image.open(io.BytesIO(frame_to_jpeg(raw, w, h)))
    img.save(path, format="PNG")
