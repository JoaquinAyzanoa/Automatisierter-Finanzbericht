@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Crear acceso directo - Automatizacion de Informes Financieros

rem Carpeta actual del proyecto (sin la barra final).
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"

rem Ubicacion del Escritorio (soporta el redireccionamiento de OneDrive).
set "DESK=%USERPROFILE%\Desktop"
if not exist "%DESK%" set "DESK=%USERPROFILE%\OneDrive\Desktop"
if not exist "%DESK%" set "DESK=%PROJ%"

set "OUT=%DESK%\Iniciar Finanzbericht.bat"

rem Genera el lanzador con el "cd" a esta carpeta ya incrustado.
> "%OUT%" echo @echo off
>> "%OUT%" echo cd /d "%PROJ%"
>> "%OUT%" echo call "iniciar.bat"

echo Acceso directo creado en:
echo    %OUT%
echo.
echo Haz doble clic en el para arrancar la aplicacion.
echo.
pause
