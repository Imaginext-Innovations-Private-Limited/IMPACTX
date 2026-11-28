@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Start START_WINDOWS.bat once before installing voice input.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-voice.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" setup_voice.py
if errorlevel 1 goto failed
echo Local speech engine tested. Open the project in Chrome or Edge and allow microphone access.
pause
exit /b 0
:failed
echo Voice setup failed. Read SETUP.md. Typed input remains available.
pause
exit /b 1
