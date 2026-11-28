@echo off
setlocal
title CareerPilot AI - First-time Setup
cd /d "%~dp0"
if errorlevel 1 (
    echo ERROR: Could not open the CareerPilot AI project folder.
    goto :failed
)

call :find_python
if errorlevel 1 goto :failed

echo.
echo Setting up CareerPilot AI. This can take a few minutes the first time.
%PYTHON_COMMAND% setup_windows.py prepare
if errorlevel 1 goto :failed

echo.
echo Setup completed successfully.
echo You can now double-click start_project.bat to run CareerPilot AI.
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
echo Setup did not complete because of the error above.
echo Fix the issue and double-click this file again. Nothing in the database was reset.
pause
exit /b 1

:finished
pause
exit /b 0
