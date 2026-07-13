@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Setup - Automatizacion de Informes Financieros

echo ============================================
echo    Setup: instalacion de dependencias
echo ============================================
echo.

if not exist "backend\.env" ( copy "backend\.env.example" "backend\.env" >nul & echo [ok] Creado backend\.env - revisa ADMIN_USER / ADMIN_PASSWORD )

echo [..] Backend: uv sync ...
pushd backend & uv sync & popd

echo [..] Frontend: npm install ...
pushd frontend & npm install & popd

echo.
echo Setup completo.
echo  - Ejecuta "crear-acceso-directo.bat" para crear el lanzador en el Escritorio.
echo  - O haz doble clic en "iniciar.bat" para arrancar la app.
echo.
pause
