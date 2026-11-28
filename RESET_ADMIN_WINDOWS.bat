@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run SETUP_MYSQL.bat and START_WINDOWS.bat first.
 pause
 exit /b 1
)
echo This replaces the Welfare Navigator admin password and signs out existing admin sessions.
choice /C YN /N /M "Generate a new password file? [Y/N] "
if errorlevel 2 exit /b 0
".venv\Scripts\python.exe" run.py --issue-admin-file
if errorlevel 1 (
 echo Check the MySQL connection and that your project folder is writable.
 pause
 exit /b 1
)
pause
