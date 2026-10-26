@echo off
chcp 65001 >nul
title Setup - Photo Selector (one click)
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "BINDIR=%~dp0tools\bin"
set "UVEXE="

echo ============================================================
echo  Photo Selection Assistant - one click setup
echo ------------------------------------------------------------
echo  step 1  create virtual environment (.venv)
echo  step 2  install dependencies
echo  step 3  run all tests to verify
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" goto have_venv

echo [1/3] Creating virtual environment ...
call :venv_with_python
if exist ".venv\Scripts\python.exe" goto have_venv
echo        python -m venv failed, trying uv ...
call :ensure_uv
if not defined UVEXE goto no_uv
"%UVEXE%" venv --python 3.13 .venv
if exist ".venv\Scripts\python.exe" goto have_venv
echo [X] uv venv also failed.
goto venv_failed

:have_venv
echo        .venv ready
echo.
echo [2/3] Installing dependencies ...
echo        mirror: %MIRROR%
call :ensure_uv
if defined UVEXE goto deps_with_uv
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i %MIRROR%
if not errorlevel 1 goto run_tests
echo [!] Mirror failed, retrying default PyPI ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto deps_failed
goto run_tests

:deps_with_uv
"%UVEXE%" pip install --python ".venv\Scripts\python.exe" -r requirements.txt --index-url %MIRROR%
if not errorlevel 1 goto run_tests
echo [!] Mirror failed, retrying default PyPI ...
"%UVEXE%" pip install --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 goto deps_failed

:run_tests
echo.
echo [3/3] Verifying environment (running all tests) ...
echo ------------------------------------------------------------
".venv\Scripts\python.exe" tests\run_all.py
if errorlevel 1 goto tests_failed

echo.
echo ============================================================
echo  SETUP OK
echo ------------------------------------------------------------
echo  Next: double click the START bat file in this folder.
echo  The browser will open http://localhost:8501
echo.
echo  Double click files in this folder:
dir /b *.bat
echo ============================================================
pause
exit /b 0

rem ---------------------------------------------------------- sub: venv
:venv_with_python
if exist ".venv" rmdir /s /q ".venv" 2>nul
py -3.13 -m venv .venv 2>nul && exit /b 0
if exist ".venv" rmdir /s /q ".venv" 2>nul
py -3 -m venv .venv 2>nul && exit /b 0
if exist ".venv" rmdir /s /q ".venv" 2>nul
python -m venv .venv 2>nul && exit /b 0
exit /b 1

rem ---------------------------------------------------------- sub: uv
:ensure_uv
if defined UVEXE exit /b 0
if exist "%BINDIR%\uv.exe" set "UVEXE=%BINDIR%\uv.exe" & exit /b 0
where uv >nul 2>nul
if errorlevel 1 goto uv_download
for /f "delims=" %%P in ('where uv') do set "UVEXE=%%P"
exit /b 0

:uv_download
echo        uv not found, downloading it (about 60 MB) ...
if not exist "%BINDIR%" mkdir "%BINDIR%"
curl.exe -L --retry 2 --connect-timeout 20 -o "%BINDIR%\uv.zip" "https://gh-proxy.com/https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
if not exist "%BINDIR%\uv.zip" exit /b 1
tar -xf "%BINDIR%\uv.zip" -C "%BINDIR%" >nul 2>nul
del "%BINDIR%\uv.zip" >nul 2>nul
if exist "%BINDIR%\uv.exe" set "UVEXE=%BINDIR%\uv.exe" & exit /b 0
exit /b 1

rem ---------------------------------------------------------- errors
:no_uv
echo.
echo [X] Cannot create .venv on this machine.
echo     Python looks broken (ensurepip failed) and uv is not available.
echo.
echo     Fix option A - install Python 3.13 (recommended):
echo        winget install Python.Python.3.13
echo     Fix option B - install uv:
echo        winget install astral-sh.uv
echo     Then run this file again.
echo.
pause
exit /b 1

:venv_failed
echo.
echo [X] Failed to create .venv
echo     Check disk space and permissions, then run again.
echo.
pause
exit /b 1

:deps_failed
echo.
echo [X] Failed to install dependencies.
echo     Check network or proxy, then run again.
echo.
pause
exit /b 1

:tests_failed
echo.
echo [X] Dependencies installed, but some tests failed (see above).
echo     Send the first failing test name to the team leader.
echo.
pause
exit /b 1
