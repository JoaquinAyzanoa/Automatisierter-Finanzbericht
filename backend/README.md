# Finanzbericht Backend

FastAPI backend for automated Excel finance-report generation. Uses SQLite and `uv` (Python 3.13).

## Setup

```bash
cd backend
uv sync                 # install deps into .venv
cp .env.example .env    # adjust as needed
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The backend runs on **:8000** (the frontend dev server uses :3000 and proxies `/api` here).

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Test

```bash
uv run pytest
```

## Layout

See the "Backend Structure (FastAPI)" section in the root `CLAUDE.md`.
Layers: **API (routes) → Services → Repositories → Models**.
