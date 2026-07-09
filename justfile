# Justfile for Automatisierter-Finanzbericht
# Run `just` to list available recipes.

# On Windows, just defaults to `sh` (not present). Use cmd.exe, which also
# supports the `&&` used below. Other platforms keep the default sh.
set windows-shell := ["cmd.exe", "/c"]

backend_dir := "backend"
frontend_dir := "frontend"

# List available recipes
default:
    @just --list

# Run the backend dev server (FastAPI + uvicorn) with auto-reload
run-backend:
    cd {{backend_dir}} && uv run uvicorn app.main:app --reload --port 8000

# Run the frontend dev server (Vite)
run-frontend:
    cd {{frontend_dir}} && npm run dev

# Install/sync backend dependencies
install-backend:
    cd {{backend_dir}} && uv sync

# Install frontend dependencies
install-frontend:
    cd {{frontend_dir}} && npm install

# Install both backend and frontend dependencies
install: install-backend install-frontend

# Run the backend test suite
test-backend:
    cd {{backend_dir}} && uv run pytest

# Build the frontend for production
build-frontend:
    cd {{frontend_dir}} && npm run build
