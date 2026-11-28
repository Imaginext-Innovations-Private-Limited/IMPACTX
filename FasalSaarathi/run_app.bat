@echo off
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title FasalSaarathi - Farm Advisor
echo ============================================================
echo   Starting FasalSaarathi Server on http://127.0.0.1:5000
echo ============================================================
echo.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i=0; $i -lt 40; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/status' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:5000'; break } } catch {} Start-Sleep -Milliseconds 500 }"
python app.py
pause
