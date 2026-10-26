@echo off
chcp 65001 >nul
title Finalize dataset - convert labels + split val + check
setlocal
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYEXE%" goto no_python

echo ============================================================
echo  Finalize dataset
echo ------------------------------------------------------------
echo  It will:
echo    1) convert the label tool's .json files into YOLO .txt
echo    2) move 20%% of photos from train to val (only if val is empty)
echo    3) check labels: format, class ids, coords, missing boxes
echo ============================================================
echo.

"%PYEXE%" tools\json2yolo.py
set "RC1=%ERRORLEVEL%"
echo.

if not "%RC1%"=="0" goto conv_failed

"%PYEXE%" tools\finalize_dataset.py %*
set "RC2=%ERRORLEVEL%"
echo.

if "%RC2%"=="0" goto ok

echo ============================================================
echo  NOT READY. Fix the red items above, then run this again.
echo  Most common:
echo    - some photos still have no boxes
echo    - a label you typed is not in classes.txt
echo ============================================================
pause
exit /b 1

:ok
echo ============================================================
echo  READY.  Next: double click the train bat.
echo ============================================================
pause
exit /b 0

:conv_failed
echo ============================================================
echo  Label conversion failed. Read the red text above.
echo ============================================================
pause
exit /b 1

:no_python
echo [ERROR] project python not found. Run the setup bat first.
echo.
pause
exit /b 1
