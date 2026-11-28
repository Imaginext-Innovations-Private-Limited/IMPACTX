@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install "PyMySQL[rsa]>=1.1,<2"
if errorlevel 1 goto done
".venv\Scripts\python.exe" setup_mysql.py
:done
pause
