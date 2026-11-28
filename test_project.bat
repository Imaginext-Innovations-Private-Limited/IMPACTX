@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run run.bat once to set up dependencies & pause & exit /b 1)
.venv\Scripts\python.exe -m pytest tests -v -s
set RESULT=%errorlevel%
echo Test exit code: %RESULT%
pause
exit /b %RESULT%
