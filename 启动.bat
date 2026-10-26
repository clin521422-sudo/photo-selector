@echo off
chcp 65001 >nul
title Photo Selector - Streamlit
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if not exist ".venv\Scripts\python.exe" goto no_venv

call ".venv\Scripts\activate.bat"

echo ============================================================
echo  Photo Selection Assistant
echo ============================================================
echo  URL: http://localhost:8501
echo  The browser will open in a few seconds.
echo  Close this window to stop the server.
echo.

rem Open the browser after the server is ready (about 8 seconds from now).
rem Set NOSTART=1 in the environment to skip opening the browser.
if not defined NOSTART start "" /b cmd /c "ping -n 9 127.0.0.1 >nul & start http://localhost:8501"

rem --server.headless true : do NOT touch %%USERPROFILE%%\.streamlit
rem (that folder may be blocked by security software; headless mode skips it)
python -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false

echo.
echo Streamlit stopped.
pause
exit /b 0

:no_venv
echo [ERROR] .venv not found in this folder:
echo    %~dp0
echo.
echo Please build the environment first:
echo    python -m venv .venv
echo    .venv\Scripts\activate
echo    pip install -r requirements.txt
echo.
pause
exit /b 1
