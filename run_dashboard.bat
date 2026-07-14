@echo off
setlocal enabledelayedexpansion

echo ==============================================================
echo   Project ASTRA Startup Assistant
echo ==============================================================

:: Find the ml folder without parenthesized IF blocks
if exist "PredictaGuard-main\ml" goto :found_parent
if exist "ml" goto :found_local

echo [ERROR] Could not find the 'ml' directory.
echo Please run this script from the project folder containing 'ml' or 'PredictaGuard-main'.
pause
exit /b 1

:found_parent
set "ML_DIR=PredictaGuard-main\ml"
goto :cd_to_ml

:found_local
set "ML_DIR=ml"
goto :cd_to_ml

:cd_to_ml
cd "%ML_DIR%"
echo Working in directory: %CD%

:: Check if virtual environment exists
if exist ".venv" goto :activate_venv

echo [WARNING] .venv directory not found! Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 goto :venv_fail

echo [INFO] Virtual environment created successfully.
echo Installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt
goto :check_models

:venv_fail
echo [ERROR] Failed to create virtual environment. Do you have Python installed and on your PATH?
pause
exit /b 1

:activate_venv
call .venv\Scripts\activate

:check_models
:: Check if models exist
if exist "models\skab_best_model.joblib" goto :start_server

echo [INFO] Model files are missing (gitignored). Generating mock models/data...
python generate_mock_models.py

:start_server
echo [INFO] Starting the Project ASTRA API and Dashboard...
echo Open http://localhost:8000/ in your browser once the server starts.
echo Press CTRL+C in this terminal window to stop the server.
echo --------------------------------------------------------------

python -X utf8 -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

pause
