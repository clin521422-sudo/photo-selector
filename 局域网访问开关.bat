@echo off
chcp 65001 >nul
title LAN Access Switch - Photo Selector 8501
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

rem ---- self elevate (firewall rules need administrator) ----
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found in this folder.
    echo Build the environment first: pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" tools\lan_switch.py
echo.
pause
