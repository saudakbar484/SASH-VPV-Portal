"""Process-wide XRTechDevice singleton with self-healing frame access.



The XRTECH SDK occasionally enters a state where `XR_Vein_GetStdVeinImage`

returns the same cached bytes for every call, regardless of palm presence

or movement (we hit this empirically during recognition testing).

A dedicated capture thread reads frames once and shares them with all HTTP

callers so multiple MJPEG clients cannot pile up on the device lock.

"""

from __future__ import annotations



import hashlib

import logging

import time

from collections import deque

from threading import Event, Lock, Thread

from typing import Any, Optional



from backend.settings import XRTECH_SDK_DIR



# Imported after settings (which adds xrtech to sys.path).

from xrtech_device import XRTechDevice  # noqa: E402



logger = logging.getLogger(__name__)



_device: Optional[XRTechDevice] = None

_stream_lock = Lock()

_frame_times: deque[float] = deque(maxlen=60)



# Auto-heal state for the frame-cache freeze bug.

_AUTOHEAL_DUP_THRESHOLD = 5  # 5 identical hashes in a row -> reconnect

_AUTOHEAL_COOLDOWN_S = 3.0   # don't heal more than once every 3 seconds

_last_frame_hash: Optional[bytes] = None

_consecutive_dups = 0

_last_heal_at: float = 0.0



# Shared frame cache populated by a single background capture thread.

_CAPTURE_FPS = 15

_capture_stop = Event()

_capture_thread: Optional[Thread] = None

_latest_raw: Optional[bytes] = None

_latest_raw_lock = Lock()



# Cached identifiers. The XRTECH SDK occasionally returns garbled bytes for

# GetSerial / GetFwVersion if it has been running for a while - we capture the

# values once at init (when the SDK state is fresh) and never re-query.

_cached_serial: Optional[str] = None

_cached_fw_version: Optional[str] = None

_cached_sdk_version: Optional[str] = None





def get_device() -> XRTechDevice:

    """Return the lazily-constructed singleton; does not auto-load the DLL."""

    global _device

    if _device is None:

        _device = XRTechDevice(XRTECH_SDK_DIR)

    return _device





def ensure_loaded() -> bool:

    device = get_device()

    if device._dll is None:

        return device.load()

    return True





def reset_frame_tracking() -> None:

    """Clear FPS history and the shared frame cache."""

    global _last_frame_hash, _consecutive_dups, _last_heal_at, _latest_raw

    with _stream_lock:

        _frame_times.clear()

    with _latest_raw_lock:

        _latest_raw = None

    _last_frame_hash = None

    _consecutive_dups = 0

    _last_heal_at = 0.0





def stop_capture_loop() -> None:

    global _capture_thread

    _capture_stop.set()

    if _capture_thread is not None and _capture_thread.is_alive():

        _capture_thread.join(timeout=2.0)

    _capture_thread = None





def start_capture_loop() -> None:

    global _capture_thread

    if _capture_thread is not None and _capture_thread.is_alive():

        return

    _capture_stop.clear()

    _capture_thread = Thread(target=_capture_loop, name="xrtech-capture", daemon=True)

    _capture_thread.start()





def _init_sdk() -> dict[str, Any]:

    global _cached_serial, _cached_fw_version, _cached_sdk_version

    if not ensure_loaded():

        return {"success": False, "message": "DLL load failed", "code": -1}

    device = get_device()

    result = device.init()

    if result.get("success"):

        try:

            _cached_serial = device.get_serial_number()

        except Exception:

            _cached_serial = None

        try:

            _cached_fw_version = device.get_fw_version()

        except Exception:

            _cached_fw_version = None

        try:

            _cached_sdk_version = device.get_sdk_version()

        except Exception:

            _cached_sdk_version = None

        logger.info(

            "Cached identifiers: serial=%s fw=%s sdk=%s",

            _cached_serial, _cached_fw_version, _cached_sdk_version,

        )

    return result





def init_device() -> dict[str, Any]:

    result = _init_sdk()

    if result.get("success"):

        start_capture_loop()

    return result





def cached_serial() -> Optional[str]:

    return _cached_serial





def cached_fw_version() -> Optional[str]:

    return _cached_fw_version





def cached_sdk_version() -> Optional[str]:

    return _cached_sdk_version





def deinit_device() -> None:

    stop_capture_loop()

    reset_frame_tracking()

    device = get_device()

    try:

        device.deinit()

    except Exception:

        pass





def record_frame() -> None:

    """Track a delivered frame for FPS reporting on /api/device/stream-status."""

    with _stream_lock:

        _frame_times.append(time.monotonic())





def stream_fps() -> float:

    with _stream_lock:

        if len(_frame_times) < 2:

            return 0.0

        span = _frame_times[-1] - _frame_times[0]

        if span <= 0:

            return 0.0

        return round((len(_frame_times) - 1) / span, 1)





def stream_age_seconds() -> Optional[float]:

    with _stream_lock:

        if not _frame_times:

            return None

        return round(time.monotonic() - _frame_times[-1], 2)





def _short_hash(data: bytes) -> bytes:

    """Cheap blake2b digest for frame-equality detection (~30 us on 300 KB)."""

    return hashlib.blake2b(data, digest_size=16).digest()





def _store_frame(raw: bytes) -> bool:

    """Update cache and FPS tracking. Returns True when auto-heal is needed."""

    global _last_frame_hash, _consecutive_dups, _last_heal_at, _latest_raw



    digest = _short_hash(raw)

    should_heal = False

    with _stream_lock:

        if digest == _last_frame_hash:

            _consecutive_dups += 1

        else:

            _consecutive_dups = 0

        _last_frame_hash = digest

        now = time.monotonic()

        if (

            _consecutive_dups >= _AUTOHEAL_DUP_THRESHOLD

            and (now - _last_heal_at) >= _AUTOHEAL_COOLDOWN_S

        ):

            should_heal = True

            _last_heal_at = now

            _consecutive_dups = 0

            _last_frame_hash = None



    if should_heal:

        return True



    with _latest_raw_lock:

        _latest_raw = raw

    with _stream_lock:

        _frame_times.append(time.monotonic())

    return False





def _auto_heal_sdk() -> None:

    logger.warning(

        "Frame-cache freeze detected (%d consecutive identical frames) - "

        "auto-healing the SDK (deinit + init)",

        _AUTOHEAL_DUP_THRESHOLD,

    )

    reset_frame_tracking()

    device = get_device()

    try:

        device.deinit()

    except Exception:

        pass

    result = _init_sdk()

    if not result.get("success"):

        logger.error("Auto-heal failed: %s", result.get("message"))





def _capture_loop() -> None:

    interval = 1.0 / _CAPTURE_FPS

    while not _capture_stop.is_set():

        device = get_device()

        if not device.is_connected():

            time.sleep(0.2)

            continue

        try:

            raw = device.get_frame()

        except Exception:

            logger.exception("Capture loop get_frame failed")

            time.sleep(0.2)

            continue

        if raw is None:

            time.sleep(interval)

            continue

        if _store_frame(raw):

            _auto_heal_sdk()

            time.sleep(0.3)

            continue

        time.sleep(interval)





def get_fresh_frame(max_wait_s: float = 0.75) -> Optional[bytes]:

    """Return the latest cached raw frame (non-blocking for other HTTP clients)."""

    deadline = time.monotonic() + max_wait_s

    while time.monotonic() < deadline:

        age = stream_age_seconds()

        with _latest_raw_lock:

            raw = _latest_raw

        if raw is not None and age is not None and age <= max(0.5, max_wait_s):

            return raw

        if not _capture_stop.is_set():

            time.sleep(0.05)

        else:

            break

    with _latest_raw_lock:

        return _latest_raw


