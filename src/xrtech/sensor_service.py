#!/usr/bin/env python3
"""
Minimal HTTP sensor service for non-Python clients.
Run: python sensor_service.py  ->  http://localhost:5000
"""
from __future__ import annotations

import atexit
import base64
import signal
import sys
import time

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

from xrtech_device import XRTechDevice, frame_to_jpeg

app = Flask(__name__)
CORS(app)
DEVICE = XRTechDevice()


@app.route("/api/device/status")
def device_status():
    return jsonify({
        "loaded": DEVICE._dll is not None,
        "connected": DEVICE.is_connected(),
        "img_size": f"{XRTechDevice.IMG_W}x{XRTechDevice.IMG_H}",
        "feat_size": DEVICE._feat_size if DEVICE.is_connected() else None,
    })


@app.route("/api/device/init", methods=["POST"])
def device_init():
    if not DEVICE._dll and not DEVICE.load():
        return jsonify({"success": False, "message": "DLL load failed"}), 500
    return jsonify(DEVICE.init())


@app.route("/api/device/deinit", methods=["POST"])
def device_deinit():
    DEVICE.deinit()
    return jsonify({"success": True})


@app.route("/api/frame")
def get_frame():
    raw = DEVICE.get_frame()
    if not raw:
        return Response(b"", status=503, mimetype="image/jpeg")
    return Response(frame_to_jpeg(raw), mimetype="image/jpeg",
                    headers={"Cache-Control": "no-cache"})


@app.route("/api/stream")
def video_stream():
    def generate():
        boundary = b"--frame"
        while True:
            if not DEVICE.is_connected():
                time.sleep(0.1)
                continue
            raw = DEVICE.get_frame()
            if not raw:
                time.sleep(0.05)
                continue
            jpeg = frame_to_jpeg(raw)
            yield (
                boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                + jpeg + b"\r\n"
            )
            time.sleep(0.033)

    return Response(
        stream_with_context(generate()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


@app.route("/api/capture", methods=["POST"])
def api_capture():
    if not DEVICE.is_connected():
        return jsonify({"success": False, "message": "Device not connected"}), 503
    feat, diag = DEVICE.capture_feature(max_tries=30)
    return jsonify({
        "success": feat is not None,
        "feature_b64": base64.b64encode(feat).decode() if feat else None,
        "diagnostics": diag,
    })


@app.route("/api/match", methods=["POST"])
def api_match():
    data = request.get_json(force=True) or {}
    probe_b64 = data.get("probe") or data.get("feature")
    template_b64 = data.get("template")
    if not probe_b64 or not template_b64:
        return jsonify({"success": False, "message": "probe and template required"}), 400
    probe = base64.b64decode(probe_b64)
    template = base64.b64decode(template_b64)
    matched, dist = DEVICE.match(probe, template)
    return jsonify({"success": True, "matched": matched, "distance": dist})


def _shutdown(*_):
    DEVICE.deinit()
    if _:
        sys.exit(0)


if __name__ == "__main__":
    print("XRTECH Sensor Service — loading SDK...")
    if DEVICE.load():
        init = DEVICE.init()
        print("Device init:", init.get("message", init))
    else:
        print("DLL load failed — POST /api/device/init after fixing SDK path")
    atexit.register(_shutdown)
    for sig in (signal.SIGINT, signal.SIGTERM, getattr(signal, "SIGBREAK", signal.SIGTERM)):
        try:
            signal.signal(sig, _shutdown)
        except (ValueError, OSError):
            pass
    print("Listening on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
