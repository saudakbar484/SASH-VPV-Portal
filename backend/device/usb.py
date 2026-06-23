"""USB device enumeration via libusb-1.0 ctypes (diagnostics for /api/device/usb)."""
from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

from backend.settings import XRTECH_SDK_DIR

XRTECH_VID = 0xA7A9
XRTECH_PID = 0x0620


class _LibusbDeviceDescriptor(ctypes.Structure):
    _fields_ = [
        ("bLength", ctypes.c_uint8),
        ("bDescriptorType", ctypes.c_uint8),
        ("bcdUSB", ctypes.c_uint16),
        ("bDeviceClass", ctypes.c_uint8),
        ("bDeviceSubClass", ctypes.c_uint8),
        ("bDeviceProtocol", ctypes.c_uint8),
        ("bMaxPacketSize0", ctypes.c_uint8),
        ("idVendor", ctypes.c_uint16),
        ("idProduct", ctypes.c_uint16),
        ("bcdDevice", ctypes.c_uint16),
        ("iManufacturer", ctypes.c_uint8),
        ("iProduct", ctypes.c_uint8),
        ("iSerialNumber", ctypes.c_uint8),
        ("bNumConfigurations", ctypes.c_uint8),
    ]


def enumerate_usb() -> list[dict[str, Any]]:
    dll_path = Path(XRTECH_SDK_DIR) / "libusb-1.0.dll"
    if not dll_path.exists():
        return []
    try:
        libusb = ctypes.CDLL(str(dll_path))
    except Exception:
        return []

    try:
        libusb.libusb_init.argtypes = [ctypes.c_void_p]
        libusb.libusb_init.restype = ctypes.c_int
        libusb.libusb_exit.argtypes = [ctypes.c_void_p]
        libusb.libusb_get_device_list.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)),
        ]
        libusb.libusb_get_device_list.restype = ctypes.c_ssize_t
        libusb.libusb_free_device_list.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_int,
        ]
        libusb.libusb_get_device_descriptor.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_LibusbDeviceDescriptor),
        ]
        libusb.libusb_get_device_descriptor.restype = ctypes.c_int

        if libusb.libusb_init(None) != 0:
            return []

        dev_list = ctypes.POINTER(ctypes.c_void_p)()
        count = libusb.libusb_get_device_list(None, ctypes.byref(dev_list))
        if count < 0:
            libusb.libusb_exit(None)
            return []

        devices: list[dict[str, Any]] = []
        try:
            for i in range(count):
                desc = _LibusbDeviceDescriptor()
                if libusb.libusb_get_device_descriptor(dev_list[i], ctypes.byref(desc)) != 0:
                    continue
                devices.append(
                    {
                        "vid": f"{desc.idVendor:04x}",
                        "pid": f"{desc.idProduct:04x}",
                        "class": desc.bDeviceClass,
                        "is_xrtech": (
                            desc.idVendor == XRTECH_VID and desc.idProduct == XRTECH_PID
                        ),
                    }
                )
        finally:
            libusb.libusb_free_device_list(dev_list, 1)
            libusb.libusb_exit(None)
        return devices
    except Exception:
        return []
