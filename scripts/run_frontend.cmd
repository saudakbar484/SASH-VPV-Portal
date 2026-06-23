@echo off
REM Start the React dev server on all network interfaces (LAN access).
REM /api/* is proxied to the FastAPI backend on :8000.
cd /d "%~dp0\..\frontend"
python "%~dp0network_urls.py"
npm run dev
