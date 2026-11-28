@echo off
setlocal
title CareerPilot AI
cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Could not open the CareerPilot AI project folder.
    goto :failed
)

call :find_python
if errorlevel 1 goto :failed

echo.
echo Preparing CareerPilot AI...
%PYTHON_COMMAND% setup_windows.py prepare
if errorlevel 1 goto :failed

echo.
echo Activating the project virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate .venv.
    goto :failed
)

echo.
echo Starting the development server. Keep this window open.
python setup_windows.py start --prepared
if errorlevel 1 goto :failed
goto :finished

:find_python
set "PYTHON_COMMAND="
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.14 3.13 3.12 3.11) do (
        py -%%V -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
        if not errorlevel 1 if not defined PYTHON_COMMAND set "PYTHON_COMMAND=py -%%V"
    )
)
if defined PYTHON_COMMAND exit /b 0

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_COMMAND=python"
        exit /b 0
    )
)

echo ERROR: Compatible Python was not found.
echo Install Python 3.11, 3.12, 3.13, or 3.14 from https://www.python.org/downloads/windows/
echo Select "Add python.exe to PATH" during installation, then run this file again.
exit /b 1

:failed
echo.
echo CareerPilot AI did not start because of the error above.
echo Fix the issue and double-click this file again. Nothing in the database was reset.
pause
exit /b 1

:finished
echo.
echo The CareerPilot AI server has stopped.
pause
exit /b 0
