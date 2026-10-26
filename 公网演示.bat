@echo off
chcp 65001 >nul
title Public Demo - Photo Selector (Cloudflare Tunnel)
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\Scripts\python.exe" goto no_venv
if not exist "tools\bin\cloudflared.exe" goto no_cloudflared

echo ============================================================
echo  Photo Selector - Public Demo
echo ------------------------------------------------------------
echo  Steps:
echo    1) start local web app on port 8501
echo    2) open a public HTTPS URL (Cloudflare Quick Tunnel)
echo    3) show URL + QR code, verify it is reachable
echo  Press ENTER there to stop the tunnel when you are done.
echo ============================================================

".venv\Scripts\python.exe" tools\public_demo.py
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" echo [Exit code %RC%]
pause
exit /b %RC%

:no_venv
echo [ERROR] .venv not found in this folder:
echo    %~dp0
echo Build the environment first:
echo    python -m venv .venv
echo    .venv\Scripts\activate
echo    pip install -r requirements.txt
echo.
pause
exit /b 1

:no_cloudflared
echo [ERROR] tools\bin\cloudflared.exe not found.
echo.
echo Run this once to download it (uses gh-proxy mirror, about 53 MB):
echo    python tools\get_cloudflared.py
echo.
pause
exit /b 1
