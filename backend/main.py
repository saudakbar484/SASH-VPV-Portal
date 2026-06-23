"""FastAPI entry point for the palm vein recognition backend."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.base import create_all
from backend.db.migrate import run_migrations
from backend.db import models
from backend.device.singleton import deinit_device, ensure_loaded, init_device
from backend.routes import admin as admin_routes
from backend.routes import auth as auth_routes
from backend.routes import dashboard as dashboard_routes
from backend.routes import device as device_routes
from backend.routes import employee as employee_routes
from backend.routes import enroll as enroll_routes
from backend.routes import hardware as hardware_routes
from backend.routes import identities as identities_routes
from backend.routes import internal as internal_routes
from backend.routes import public as public_routes
from backend.routes import recognize as recognize_routes
from backend.routes import stream as stream_routes
from backend.routes import training as training_routes
from backend.routes import user as user_routes
from backend.settings import CORS_ORIGIN_REGEX, CORS_ORIGINS, RECOGNITION_LOGS_ENABLED
from sqlalchemy import delete

logger = logging.getLogger("backend")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Initialising database (create_all)...")
    create_all()
    run_migrations()

    if not RECOGNITION_LOGS_ENABLED:
        from backend.db.base import SessionLocal

        db = SessionLocal()
        try:
            n = db.execute(delete(models.RecognitionLog)).rowcount
            db.commit()
            logger.info("Recognition logs disabled — purged %s historical rows", n)
        finally:
            db.close()
    else:
        from backend.db.base import SessionLocal
        from backend.auth.attendance import close_yesterday_if_needed
        from backend.auth.template_cache import refresh_account_templates
        from backend.matcher.inference_device import configure_torch_runtime
        from backend.matcher.singleton import get_matcher

        configure_torch_runtime()
        db = SessionLocal()
        try:
            refresh_account_templates(db)
            close_yesterday_if_needed(db)
        finally:
            db.close()
        logger.info("Warming neural matcher...")
        get_matcher()
        logger.info("Recognition logging enabled")

    logger.info("Loading XRTECH SDK...")
    if not ensure_loaded():
        logger.warning("DLL load failed - POST /api/device/init after fixing path")
    else:
        result = init_device()
        if result.get("success"):
            logger.info("Sensor connected: %s", result.get("message"))
        else:
            logger.warning(
                "Sensor not connected on startup: %s. "
                "Call POST /api/device/init once the scanner is plugged in.",
                result.get("message"),
            )
    yield
    logger.info("Shutting down - releasing sensor")
    deinit_device()


app = FastAPI(
    title="Palm Vein Recognition API",
    version="0.1.0",
    description=(
        "Backend for the XRTECH MagicVein Plus + EfficientNet-B0/CBAM/ArcFace "
        "palm vein recognition system. Open /docs for the interactive API."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(user_routes.router)
app.include_router(public_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(device_routes.router)
app.include_router(stream_routes.router)
app.include_router(identities_routes.router)
app.include_router(employee_routes.router)
app.include_router(enroll_routes.router)
app.include_router(recognize_routes.router)
app.include_router(hardware_routes.router)
app.include_router(internal_routes.router)
app.include_router(training_routes.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "palm-vein-backend"}
