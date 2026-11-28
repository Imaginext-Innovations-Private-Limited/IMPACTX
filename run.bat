@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (python -m venv .venv) else (py -3 -m venv .venv)
)
if not exist ".venv\Scripts\python.exe" (echo Python setup failed. Install Python 3. & pause & exit /b 1)
if /I "%~1"=="setup" goto setup
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,pydantic,multipart,PIL,pytesseract,sklearn,httpx,pytest,sarvamai,cv2,publicsuffix2" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
)
".venv\Scripts\python.exe" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',8000)); s.close()" >nul 2>nul
if errorlevel 1 (echo Port 8000 is unavailable. Stop the previous ScamShield server with Ctrl+C and try again. & pause & exit /b 1)
if /I "%~1"=="offline" goto offline
".venv\Scripts\python.exe" tools\start_hybrid.py
set "RESULT=%errorlevel%"
goto finish
:setup
".venv\Scripts\python.exe" -m pip install -r requirements.txt
set "RESULT=%errorlevel%"
if "%RESULT%"=="0" echo Dependency setup complete. Run run.bat offline or run.bat.
goto finish
:offline
set "GROQ_API_KEY="
set "SARVAM_API_KEY="
set "GOOGLE_SAFE_BROWSING_API_KEY="
set "SAFE_BROWSING_API_KEY="
echo Offline mode: http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn scamshield.main:app --host 127.0.0.1 --port 8000
set "RESULT=%errorlevel%"
:finish
pause
exit /b %RESULT%
