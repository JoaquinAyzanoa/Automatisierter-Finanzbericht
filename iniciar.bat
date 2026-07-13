@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Automatizacion de Informes Financieros

if not exist "backend\.venv" ( echo [!] Falta instalar dependencias. Ejecuta primero setup.bat & echo. & pause & exit /b )

echo [..] Iniciando backend en http://localhost:8000
start "Backend (8000)" cmd /k "cd backend && uv run uvicorn app.main:app --reload --port 8000"

echo [..] Iniciando frontend en http://localhost:3000
start "Frontend (3000)" cmd /k "cd frontend && npm run dev"

echo [..] Abriendo el navegador...
timeout /t 6 /nobreak >nul
start "" http://localhost:3000

echo.
echo Listo. Cierra las ventanas "Backend (8000)" y "Frontend (3000)" para detener la app.
timeout /t 4 /nobreak >nul
