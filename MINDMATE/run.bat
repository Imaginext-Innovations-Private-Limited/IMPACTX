@echo off
title MINDMATE - Student Wellbeing Companion
echo ======================================================
echo   MINDMATE - Starting Backend and Frontend on Windows
echo ======================================================
echo.

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example
  )
)

echo [1/2] Starting Python FastAPI Backend on http://127.0.0.1:8000 ...
start "MINDMATE FastAPI Backend" cmd /k "python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting React + Vite Frontend on http://localhost:3000 ...
set USE_FASTAPI_PROXY=true
start "MINDMATE Frontend" cmd /k "npx vite --port 3000 --host 0.0.0.0"

echo.
echo Both services are starting in separate windows!
echo Open your browser at: http://localhost:3000
pause
