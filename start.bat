@echo off
echo.
echo =========================================
echo  Label Inpainter - Local Setup Script
echo =========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not on PATH.
    echo         Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found.

:: Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate venv and install requirements
echo [INFO] Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

:: Create .env if missing
if not exist ".env" (
    copy .env.example .env >nul
    echo.
    echo [ACTION REQUIRED] A .env file has been created.
    echo                   Open it and paste your Recraft.ai API key:
    echo.
    echo                   RECRAFT_API_KEY=your_key_here
    echo.
    echo                   Get your key from your Recraft.ai profile.
    echo.
    pause
) else (
    echo [OK] .env file exists.
)

:: Create directories
if not exist "static\uploads" mkdir static\uploads
if not exist "static\results" mkdir static\results

echo.
echo =========================================
echo  Setup complete! Starting Flask server...
echo  Open http://127.0.0.1:5000 in browser
echo =========================================
echo.

python app.py

pause
