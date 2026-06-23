"""Backend settings - paths, threshold, sensor config."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

_env_path = PROJECT_ROOT / ".env"
if _env_path.is_file():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_path)
    except ImportError:
        pass

# Make the existing palm_vein and xrtech packages importable.
for path in (SRC_DIR, SRC_DIR / "xrtech"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

DATA_STORE_DIR = PROJECT_ROOT / "data" / "store"
USERS_REF_DIR = PROJECT_ROOT / "data" / "users"
DATASET_DIR = PROJECT_ROOT / "data" / "dataset"
FOLDER_MAPPING_CSV = DATASET_DIR / "folder_mapping.csv"
CAPTURES_DIR = USERS_REF_DIR / "_captures"
DB_PATH = DATA_STORE_DIR / "app.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

# Auth — override via environment in production
AUTH_SECRET = os.environ.get("AUTH_SECRET", "palmvein-dev-secret-change-in-production")
AUTH_TOKEN_TTL_S = 60 * 60 * 24 * 7  # 7 days

# Secured cron / scheduler hook for end-of-day attendance (empty = endpoint disabled)
ATTENDANCE_CRON_SECRET = os.environ.get("ATTENDANCE_CRON_SECRET", "")

# Recognition logs — disabled until explicitly enabled
RECOGNITION_LOGS_ENABLED = True

# Lightweight path import (no torch) - the actual checkpoint is loaded lazily.
from palm_vein.config import CHECKPOINT_PRODUCTION  # noqa: E402

# Heavy imports (torch / matcher) are loaded lazily in the routes that need them.
DEFAULT_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.40"))
LOGIN_MATCH_THRESHOLD = float(os.environ.get("LOGIN_MATCH_THRESHOLD", "0.40"))
ADMIN_MATCH_THRESHOLD = float(os.environ.get("ADMIN_MATCH_THRESHOLD", "0.40"))
LOGIN_MATCH_MIN_MARGIN = float(os.environ.get("LOGIN_MATCH_MIN_MARGIN", "0.06"))
EMBEDDING_DIM = 512  # 512-d L2-normalised float32 -> 2048 bytes per template.
INFERENCE_DEVICE = os.environ.get("INFERENCE_DEVICE", "auto")

XRTECH_SDK_DIR = (
    PROJECT_ROOT
    / "src"
    / "xrtech"
    / "sdk"
    / "XRCommonVeinPlus_V3.1.3_t113s"
    / "Library file"
    / "win_x64"
)

# SMTP — defaults to primary admin Gmail; set SMTP_PASSWORD in .env for delivery
DEFAULT_ADMIN_EMAIL = "saudakbar65367@gmail.com"
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", DEFAULT_ADMIN_EMAIL)
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", DEFAULT_ADMIN_EMAIL)
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Dev: allow phones/laptops on the same LAN (e.g. http://192.168.1.42:5173)
CORS_ORIGIN_REGEX = os.environ.get(
    "CORS_ORIGIN_REGEX",
    r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?",
)

from backend.auth.google_credentials import load_google_oauth_config

_google_oauth = load_google_oauth_config(
    PROJECT_ROOT,
    os.environ.get("GOOGLE_OAUTH_JSON", ""),
)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip() or str(
    _google_oauth.get("client_id", "")
).strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip() or str(
    _google_oauth.get("client_secret", "")
).strip()
GOOGLE_OAUTH_REDIRECT_URIS = list(_google_oauth.get("redirect_uris") or [])
GOOGLE_OAUTH_JS_ORIGINS = list(_google_oauth.get("javascript_origins") or [])

API_HOST = "0.0.0.0"
API_PORT = 8000

for d in (DATA_STORE_DIR, USERS_REF_DIR, CAPTURES_DIR, DATASET_DIR):
    d.mkdir(parents=True, exist_ok=True)
