#!/bin/bash
cd "$(dirname "$0")"

echo "[KleinSearch] Starting..."

if [ ! -f ".venv/bin/python" ]; then
    echo "[KleinSearch] Creating virtual environment..."
    python3 -m venv .venv
    echo "[KleinSearch] Installing dependencies..."
    .venv/bin/python -m pip install -U pip
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/playwright install chromium
fi

echo "[KleinSearch] Executing main app..."
export PYTHONPATH=src
.venv/bin/python src/main.py
