"""Launch the FastAPI backend with uvicorn."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for p in (PROJECT_ROOT, PROJECT_ROOT / "src", PROJECT_ROOT / "src" / "xrtech", PROJECT_ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import uvicorn  # noqa: E402

from backend.settings import API_HOST, API_PORT  # noqa: E402
from network_urls import print_urls  # noqa: E402

if __name__ == "__main__":
    print(f"Starting backend on {API_HOST}:{API_PORT}")
    print_urls(backend_port=API_PORT)
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )
