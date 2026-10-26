@echo off
chcp 65001 >nul
title Photo Selector - Tests
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\Scripts\python.exe" goto no_venv

call ".venv\Scripts\activate.bat"
echo ============================================================
echo  Running all module tests ...
echo ============================================================
python tests\run_all.py
echo.
pause
exit /b 0

:no_venv
echo [ERROR] .venv not found. Please run pip install -r requirements.txt first.
pause
exit /b 1
