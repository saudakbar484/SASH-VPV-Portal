# XRTECH Portable Kit

Copy this entire folder into any project. Everything needed to run the **XRTECH MagicVein Plus** USB palm vein scanner (VID `0xA7A9`, PID `0x0620`) on Windows x64.

## Contents

```
XRTECH_Portable_Kit/
├── xrtech_device.py          # Python ctypes wrapper (use directly)
├── sensor_service.py         # Optional Flask HTTP API (port 5000)
├── example_main.py           # Smoke test script
├── requirements.txt
├── XRTECH_SETUP.md           # Full integration guide
├── output/                   # Created by example_main.py
└── sdk/
    └── XRCommonVeinPlus_V3.1.3_t113s/
        ├── Library file/win_x64/
        │   ├── XRCommonVeinPlusAPI.dll
        │   └── libusb-1.0.dll
        ├── Header file/          # C API reference
        └── Sample/ApiSample.cpp  # Vendor enrollment sample
```

## Prerequisites

1. **Windows 10/11 x64**
2. **Python 3.10+**
3. **Zadig driver** — bind WinUSB or libusbK for VID `A7A9` / PID `0620`
   - https://zadig.akeo.ie/

## Quick start

```bash
cd XRTECH_Portable_Kit
pip install -r requirements.txt
python example_main.py
```

Expected: `output/test_frame.jpg` and optionally `output/test_feature.b64`.

## Use in your Python project

```python
from xrtech_device import XRTechDevice

dev = XRTechDevice()          # auto-finds sdk/.../win_x64
dev.load()
dev.init()
frame = dev.get_frame()
feat, diag = dev.capture_feature()
dev.deinit()
```

Or pass a custom SDK path:

```python
dev = XRTechDevice(r"C:\my_app\sdk\...\win_x64")
```

## HTTP service (for non-Python apps)

```bash
python sensor_service.py
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/device/status` | GET | Connection info |
| `/api/device/init` | POST | Connect scanner |
| `/api/frame` | GET | Single JPEG frame |
| `/api/stream` | GET | MJPEG live preview |
| `/api/capture` | POST | Extract palm feature (base64) |
| `/api/match` | POST | `{"probe":"b64","template":"b64"}` |

HTML preview: `<img src="http://localhost:5000/api/stream" />`

## Integration approaches

| Your project | What to use |
|--------------|-------------|
| Python on same PC | `xrtech_device.py` only |
| C#, Java, Node, etc. | `sensor_service.py` + HTTP calls |
| Copy into existing app | Copy whole `XRTECH_Portable_Kit/` folder |

See **XRTECH_SETUP.md** for full API reference, enrollment flows, and troubleshooting.
