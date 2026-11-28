@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run START_WINDOWS.bat first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto failed
".venv\Scripts\python.exe" check_mysql.py
if errorlevel 1 goto failed
".venv\Scripts\python.exe" maintenance.py health
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo A self-check failed. Read the test name and message above.
pause
exit /b 1
