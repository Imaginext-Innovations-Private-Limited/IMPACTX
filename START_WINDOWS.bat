@echo off
setlocal
cd /d "%~dp0"
if not exist "local_data\mysql.json" (
 echo Install MySQL Server, then run SETUP_MYSQL.bat in this folder first.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 where py >nul 2>nul
 if errorlevel 1 (
  python -m venv .venv
 ) else (
  py -3.11 -m venv .venv
  if errorlevel 1 py -3.12 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
 )
)
if not exist ".venv\Scripts\python.exe" goto failed
if not exist ".venv\setup-mysql-v2.ok" (
 ".venv\Scripts\python.exe" -m pip install -r requirements-core.txt
 if errorlevel 1 goto failed
 ".venv\Scripts\python.exe" -m pip install "chromadb>=1,<2"
 if errorlevel 1 echo Chroma is unavailable. Local MySQL search is enabled. See SETUP.md to retry.
 echo OK>".venv\setup-mysql-v2.ok"
)
".venv\Scripts\python.exe" run.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup did not complete. Install 64-bit Python 3.11 or 3.12, check the Internet connection, and open SETUP.md.
pause
exit /b 1
