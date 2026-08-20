@echo off
setlocal

set "DIR=%~dp0"

set "PY="
where python >nul 2>nul
if %ERRORLEVEL% == 0 set "PY=python"

if "%PY%"=="" (
    where py >nul 2>nul
    if %ERRORLEVEL% == 0 set "PY=py"
)

if "%PY%"=="" (
    echo [ERROR] No se encontro Python en el PATH.
    echo         Instala Python desde https://www.python.org/downloads/
    echo         (asegurate de marcar "Add Python to PATH" al instalar).
    exit /b 127
)

"%PY%" "%DIR%run.py" %*
