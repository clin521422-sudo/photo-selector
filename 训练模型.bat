@echo off
chcp 65001 >nul
title Train custom YOLO model
setlocal
cd /d "%~dp0"
set "PYEXE=%~dp0.venv\Scripts\python.exe"
set "TRAINPY=%~dp0..\yolo\.venv\Scripts\python.exe"

if not exist "%TRAINPY%" goto no_env
if not exist "%PYEXE%" goto no_env

echo ============================================================
echo  Train custom model  (uses the yolo env with torch)
echo ------------------------------------------------------------
echo  It will:
echo    1) ask which dataset to use
echo    2) train a YOLO model on it
echo    3) export ONNX into the models folder
echo.
echo  Tip: 30 epochs is enough to test the whole pipeline.
echo       Add more later, e.g.   --epochs 120
echo ============================================================
echo.

rem pass the picked dataset name down to the python script
for /f "delims=" %%D in ('"%PYEXE%" tools\pick_dataset.py') do set "DSNAME=%%D"
if not defined DSNAME goto pick_failed

"%TRAINPY%" "%~dp0tools\train_custom.py" --dataset "%DSNAME%" %*
set "RC=%ERRORLEVEL%"
echo.

if "%RC%"=="0" goto ok

echo ============================================================
echo  Training failed. Read the red text above.
echo  Most common:
echo    - data not finalized yet  -^> run the finalize bat first
echo    - dataset has no val photos / no boxes
echo ============================================================
pause
exit /b 1

:ok
echo ============================================================
echo  Model exported into the models folder.
echo  Last step: open config.py and set
echo      "subject_model_path": "models/YOUR_DATASET.onnx"
echo  then run the test bat.
echo ============================================================
pause
exit /b 0

:pick_failed
echo [ERROR] failed to pick a dataset. Run the label bat first.
echo.
pause
exit /b 1

:no_env
echo [ERROR] environment not found.
echo    project python : %PYEXE%
echo    training python: %TRAINPY%
echo.
echo Training needs torch + ultralytics. Set it up once:
echo    cd ..\yolo
echo    uv venv --python 3.13 .venv
echo    uv pip install torch torchvision ultralytics
echo.
pause
exit /b 1
