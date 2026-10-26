@echo off
chcp 65001 >nul
title Label Tool - X-AnyLabeling
setlocal
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
set "ANN=%~dp0..\yolo\.venv\Scripts\anylabeling.exe"
set "CFGDIR=%~dp0.toolconfig"

if not exist "%PYEXE%" goto no_python
if not exist "%ANN%" goto no_tool

rem ---- config redirect: X-AnyLabeling writes to ~/.anylabelingrc, and some
rem      machines block new files in the user profile root. Keep it local.
if not exist "%CFGDIR%" mkdir "%CFGDIR%" 2>nul
if not exist "%CFGDIR%\.anylabelingrc" echo {} > "%CFGDIR%\.anylabelingrc" 2>nul
set "USERPROFILE=%CFGDIR%"
set "HOME=%CFGDIR%"

rem ---- pick which dataset (auto creates a default one if none) ----
for /f "delims=" %%D in ('"%PYEXE%" tools\pick_dataset.py') do set "DSNAME=%%D"
if not defined DSNAME goto pick_failed
set "DS=%~dp0datasets\%DSNAME%"
if not exist "%DS%\classes.txt" goto pick_failed

rem ---- count photos ----
set "IMGNUM=0"
for /f "delims=" %%F in ('dir /b /a-d "%DS%\images\train" 2^>nul') do set /a IMGNUM+=1

if "%IMGNUM%"=="0" (
    echo ============================================================
    echo  Dataset "%DSNAME%" is ready, but no photos yet.
    echo ------------------------------------------------------------
    echo  Put your photos into:
    echo      %DS%\images\train
    echo.
    echo  Classes in this dataset:
    type "%DS%\classes.txt"
    echo.
    echo  Then double click this file again to start labeling.
    echo ============================================================
    echo.
    pause
    exit /b 0
)

echo ============================================================
echo  X-AnyLabeling - dataset "%DSNAME%"   %IMGNUM% photos
echo ------------------------------------------------------------
echo  images : %DS%\images\train
echo  labels : %DS%\labels\train
echo  classes: %DS%\classes.txt
echo.
echo  HOW TO LABEL:
echo    W          drag a box, then pick a class
echo    D / A      next / previous photo
echo    Ctrl+S     save  (autosave is ON, usually not needed)
echo    close the window when done
echo ============================================================
echo.

"%ANN%" --labels "%DS%\classes.txt" --output "%DS%\labels\train" --autosave "%DS%\images\train"
echo.
echo Labeling window closed.  Next: double click the finalize bat.
pause
exit /b 0

:no_python
echo [ERROR] project python not found:
echo    %PYEXE%
echo Run the setup bat (the one starting with 1-) first.
echo.
pause
exit /b 1

:no_tool
echo [ERROR] annotation tool not found:
echo    %ANN%
echo Install it once:
echo    cd ..\yolo
echo    .venv\Scripts\activate
echo    pip install anylabeling -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.
pause
exit /b 1

:pick_failed
echo [ERROR] failed to pick a dataset.
echo Try deleting the datasets folder and running this file again.
echo.
pause
exit /b 1
