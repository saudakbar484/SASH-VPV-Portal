"""Print LAN URLs for frontend/backend dev servers."""
from __future__ import annotations

import socket


def get_lan_ipv4() -> str | None:
    """Best-effort local IPv4 on the active network (Wi‑Fi / Ethernet)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def format_urls(frontend_port: int = 5173, backend_port: int = 8000) -> list[str]:
    ip = get_lan_ipv4()
    lines = [
        f"  Local:   http://localhost:{frontend_port}/",
        f"  Network: http://{ip}:{frontend_port}/" if ip else "  Network: (could not detect LAN IP — run ipconfig)",
    ]
    if ip:
        lines.append(f"  API (direct): http://{ip}:{backend_port}/api/health")
    return lines


def print_urls(frontend_port: int = 5173, backend_port: int = 8000) -> None:
    print("")
    print("Open the site from another phone or laptop on the same Wi‑Fi:")
    for line in format_urls(frontend_port, backend_port):
        print(line)
    print("")
    print("Use the Network URL above on other devices. Keep both backend and frontend running.")
    print("If the page does not load, allow ports 5173 (and 8000) in Windows Firewall.")
    print("")


if __name__ == "__main__":
    print_urls()
