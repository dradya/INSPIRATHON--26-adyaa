@echo off
title Aegis Web Application
echo ============================================================
echo   Starting Aegis Web Application...
echo   Opening in your default browser at http://127.0.0.1:8000
echo ============================================================
cd /d "%~dp0\aegis"
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Backend exited or failed to start.
    pause
)
