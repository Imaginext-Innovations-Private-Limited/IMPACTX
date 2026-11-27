@echo off
echo ============================================================
echo   Farm Advisor — Sprint 4   (FastAPI + React Vite)
echo ============================================================
echo.

REM ── Backend ──────────────────────────────────────────────────
echo [1/2] Starting FastAPI backend on http://localhost:8000 ...
start "FarmAdvisor Backend" cmd /k "cd /d C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor\backend && C:\Users\Lokesh\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn main:app --reload --port 8000"

REM Give backend 3 seconds to start
timeout /t 3 /nobreak >nul

REM ── Frontend ─────────────────────────────────────────────────
echo [2/2] Starting Vite dev server on http://localhost:5173 ...
start "FarmAdvisor Frontend" cmd /k "set PATH=C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor\nodejs\node-v20.18.0-win-x64;%PATH% && cd /d C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor\frontend && npm run dev"

echo.
echo ============================================================
echo   Both servers starting in separate windows.
echo   Open: http://localhost:5173
echo ============================================================
echo.
pause
