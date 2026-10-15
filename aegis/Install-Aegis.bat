@echo off
setlocal
cd /d "%~dp0"

echo =======================================================
echo          Aegis - Privacy-First AI File Manager
echo                     Setup Wizard
echo =======================================================
echo.

if exist "..\AegisSetup.exe" (
    echo Launching Aegis Setup Executable...
    start "" "..\AegisSetup.exe"
    exit /b 0
)

if exist "AegisSetup.exe" (
    echo Launching Aegis Setup Executable...
    start "" "AegisSetup.exe"
    exit /b 0
)

if exist "dist\AegisSetup.exe" (
    echo Launching Aegis Setup Executable from dist...
    start "" "dist\AegisSetup.exe"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    echo Launching Aegis Setup Wizard...
    start "" pythonw installer.py
    exit /b 0
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Launching Aegis Setup Wizard...
    start "" python installer.py
    exit /b 0
)

echo Error: Neither AegisSetup.exe nor Python was found.
pause
exit /b 1
