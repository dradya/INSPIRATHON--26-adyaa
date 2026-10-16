@echo off
setlocal
pushd "%~dp0aegis"
py app.py
set "exitCode=%ERRORLEVEL%"
popd
exit /b %exitCode%