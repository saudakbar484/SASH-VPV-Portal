# SASH-VPV Portal

## Project team

**University:** National University of Technology (NUTECH), Islamabad

| Role | Name | Email |
|------|------|-------|
| Project Lead | Syed Muhamamd Huzaifa Chishty | muhammadhuzaifaf22@nutech.edu.pk |
| Member | Shanza Rahim | shanzarahimf22@nutech.edu.pk |
| Member | Saud Akbar | saudakbarf22@nutech.edu.pk |
| Supervisor | Dr. Benish Fida (HoD Artificial Intelligence) | benish.fida@nutech.edu.pk |

**Dataset:** [SASH-VPV on Kaggle](https://www.kaggle.com/datasets/sashinoventures/sash-vpv-subcutaneous-vascular-palm-vein-data) — full corpus (2,667 images, 122 subjects) in `data/raw/img/`

## Project layout

```
├── data/
│   ├── raw/img/              # SASH-VPV dataset (2,667 images, 122 subjects)
│   └── processed/            # metadata.csv, visibility_tags.csv, cv_folds.csv
├── models/checkpoints/
│   ├── production/           # checkpoint_production_full.pt (deploy this)
│   ├── validation/           # checkpoint_validation_fold0_held_out.pt
│   └── legacy/               # checkpoint.pt (CPU baseline)
├── src/
│   ├── palm_vein/            # Core Python package (model, deployment)
│   └── xrtech/               # XRTECH MagicVein Plus SDK ctypes wrapper
├── backend/                  # FastAPI service (device, stream, enroll, recognize, hardware)
├── frontend/                 # React 19 + Vite + Tailwind v4 + shadcn/ui web app
├── scripts/                  # CLI entry points + run_backend.py / run_frontend.cmd
├── training/gpu/             # GPU training wrappers + setup docs
├── tests/live/               # Real-time capture testing (enroll/ + probe/)
├── outputs/                  # metrics, logs, figures
├── docs/                     # PROJECT_PLAN.md, notes, reports
└── archive/                  # Old zip backups
```

## Quick start

```bash
python -m venv venv
venv\Scripts\activate
pip install torch  # install CUDA build from pytorch.org if using GPU
pip install -r requirements.txt
```

## Common commands

| Task | Command |
|------|---------|
| Build metadata | `python scripts/build_metadata.py` |
| Tag visibility | `python scripts/tag_visibility.py` |
| Split CV folds | `python scripts/split_folds.py` |
| Train (production) | `python scripts/train_production.py` |
| Evaluate open-set | `python scripts/evaluate.py` |
| Deployment demo | `python scripts/deploy_demo.py` |
| Live photo test | `python scripts/live_test.py` |
| Tkinter dev capture | `python scripts/live_capture_test.py` |
| Backend (FastAPI) | `python scripts/run_backend.py` |
| Frontend (Vite) | `scripts\run_frontend.cmd` |

## Deployment model

Use `models/checkpoints/production/checkpoint_production_full.pt` with `PalmVeinBiometricSystem` from `src/palm_vein/deployment.py`.

## Web application

Full-stack live recognition system using the XRTECH MagicVein Plus sensor.

**Architecture**

- **Backend** — FastAPI + SQLAlchemy/SQLite + uvicorn. Wraps the XRTECH SDK and exposes device control, MJPEG streaming, enrollment sessions, 1:1 verify, 1:N identify, and recognition logs.
- **Frontend** — React 19 + Vite 5 + Tailwind v4 + shadcn/ui + TanStack Query + Zustand. Six pages: Live Preview, Enrollment (multi-capture wizard), Recognition (Verify / Identify tabs), Identities (enrolled + 244 trained dataset classes), Logs (history + accept/reject chart), Device Control (LED palette + volume + sleep).

**Run it (two terminals)**

```bash
# Terminal 1 — backend on :8000
python scripts/run_backend.py

# Terminal 2 — frontend on :5173
scripts\run_frontend.cmd
# or: cd frontend && npm install && npm run dev
```

Then open `http://localhost:5173/` on this PC, or use the **Network** URL on other devices (same Wi‑Fi).

**LAN access (phone / other laptop)**

1. Start backend: `python scripts/run_backend.py`
2. Start frontend: `scripts\run_frontend.cmd`
3. Run `python scripts/network_urls.py` — copy the **Network** URL (e.g. `http://192.168.1.42:5173/`)
4. Open that URL on any device on the same Wi‑Fi

If the page does not load from another device, run `scripts\allow_lan_firewall.ps1` **as Administrator** once to open ports 5173 and 8000.

> **Google sign-in from a phone:** add `http://YOUR_LAN_IP:5173` to *Authorized JavaScript origins* in the Google Cloud OAuth client.

**SDK auto-heal**

The XRTECH SDK occasionally returns identical cached frames or garbled identifier strings after extended use. `backend/device/singleton.py` mitigates both: `get_fresh_frame()` watches for 5 consecutive identical frame hashes and transparently reconnects, and serial/firmware/SDK version are cached once at init while the SDK state is fresh.

## Documentation

- Design rationale: `docs/PROJECT_PLAN.md`
- Build summary: `docs/FINAL_SUMMARY.md`
- GPU setup: `training/gpu/SETUP.md`
