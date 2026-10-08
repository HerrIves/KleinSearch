@echo off
cd /d "%~dp0"

echo [KleinSearch] Starting...

if not exist ".venv\Scripts\python.exe" (
    echo [KleinSearch] Creating virtual environment...
    python -m venv .venv
    echo [KleinSearch] Installing dependencies...
    .venv\Scripts\python -m pip install -U pip
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\playwright install chromium
)

echo [KleinSearch] Executing main app...
set PYTHONPATH=src
.\.venv\Scripts\python src\main.py
if %ERRORLEVEL% NEQ 0 pause
