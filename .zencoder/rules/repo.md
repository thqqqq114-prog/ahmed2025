# Repository Profile

- **Project Name**: FarmApp (Desktop + Server)
- **Short Description**: Desktop farm management app (PySide6) with local SQLite DB, reporting, invoicing, and an optional server for licensing and app updates.
- **Primary Language/Framework**: Python 3.12, PySide6 (Qt), SQLAlchemy
- **Package Manager / Build Tool**: pip, PyInstaller (via build_exe.ps1)
- **Entry Points (apps/services/scripts)**:
  - Desktop: `app/main.py`
  - Server API: `server/api/main.py` (FastAPI)
  - Update hosting: static files under `server/updates/win/`
  - Build script (desktop): `build_exe.ps1`
- **How to Run (dev)**:
  1. Create venv: `python -m venv venv` (Windows) then `venv\Scripts\Activate.ps1`
  2. Install deps: `pip install -r requirements.txt`
  3. Run desktop app: `python -m app.main`
- **How to Build/Package**:
  - Windows EXE: Run `powershell -ExecutionPolicy Bypass -File build_exe.ps1`. Output in `dist/FarmApp/`.
- **How to Test**:
  - `pytest` (tests in `tests/`). Example: `pytest -q`.
- **Environments/Configs**:
  - Desktop:
    - UI theme: `app/ui/style.qss` auto-loaded by `app/main.py`
    - Settings stored via `app.data.database.get_setting/set_setting`
    - Update manifest URL default: `app/updater.py` -> `DEFAULT_MANIFEST`
  - Server:
    - Caddyfile.* for TLS and routing
    - `server/updates/win/manifest.json` serves desktop updater
- **CI/CD (if any)**: Not configured
- **Known Issues / TODOs**:
  - Add SHA256 validation in updater before running installer
  - Expand unit tests beyond DB test
  - Package DB migrations (Alembic) for server API when DB added
- **Contacts/Owners**: Ahmed Hussein

## Directory Structure (high-level)
- app/: Desktop application (UI, data, logic)
- server/: API and static updates hosting (Dockerized)
- tests/: Basic tests
- venv/: Virtual environment (local)

## Setup Steps
1. Install Python 3.12 and Git.
2. Create venv and install requirements.
3. Run desktop app, seed initial admin via AuthService on first start.

## Notes
- Update hosting domain and API endpoints configurable via settings.
- Build script bundles style.qss and initial SQLite DB.