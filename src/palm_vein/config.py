"""Central path configuration for the palm vein recognition project."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Data
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "img"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
METADATA_CSV = DATA_PROCESSED / "metadata.csv"
VISIBILITY_CSV = DATA_PROCESSED / "visibility_tags.csv"
CV_FOLDS_CSV = DATA_PROCESSED / "cv_folds.csv"

# Model checkpoints
CHECKPOINTS_DIR = PROJECT_ROOT / "models" / "checkpoints"
CHECKPOINT_PRODUCTION = CHECKPOINTS_DIR / "production" / "checkpoint_production_full.pt"
CHECKPOINT_VALIDATION = CHECKPOINTS_DIR / "validation" / "checkpoint_validation_fold0_held_out.pt"
CHECKPOINT_LEGACY = CHECKPOINTS_DIR / "legacy" / "checkpoint.pt"

# Outputs
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
METRICS_DIR = OUTPUTS_DIR / "metrics"
LOGS_DIR = OUTPUTS_DIR / "logs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

# Live / real-time testing (user-provided captures)
LIVE_TEST_DIR = PROJECT_ROOT / "tests" / "live"
LIVE_ENROLL_DIR = LIVE_TEST_DIR / "enroll"
LIVE_PROBE_DIR = LIVE_TEST_DIR / "probe"
LIVE_CAPTURES_DIR = LIVE_TEST_DIR / "captures"

# XRTECH MagicVein Plus sensor (NIR USB scanner, VID 0xA7A9 / PID 0x0620)
XRTECH_DIR = PROJECT_ROOT / "src" / "xrtech"
XRTECH_SDK_DIR = XRTECH_DIR / "sdk" / "XRCommonVeinPlus_V3.1.3_t113s" / "Library file" / "win_x64"
