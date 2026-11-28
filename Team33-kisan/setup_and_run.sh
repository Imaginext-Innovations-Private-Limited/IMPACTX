#!/usr/bin/env bash
set -e
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Edit .env and add GROQ_API_KEY, then re-run."; exit 0; }
echo "Open http://localhost:8000 in Chrome or Edge"
python -m uvicorn app.main:app --reload
