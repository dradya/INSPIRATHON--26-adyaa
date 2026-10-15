@echo off
setlocal
cd /d "%~dp0aegis"

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw installer.py
    exit /b 0
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    start "" python installer.py
    exit /b 0
)

if exist "%~dp0AegisSetup.exe" (
    start "" "%~dp0AegisSetup.exe"
    exit /b 0
)

if exist "AegisSetup.exe" (
    start "" "AegisSetup.exe"
    exit /b 0
)

if exist "dist\AegisSetup.exe" (
    start "" "dist\AegisSetup.exe"
    exit /b 0
)

echo Error: Neither Python nor AegisSetup.exe was found.
pause
exit /b 1
