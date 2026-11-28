@echo off
call .venv\Scripts\activate
echo Open http://localhost:8000 in Chrome or Edge
python -m uvicorn app.main:app --reload
pause
