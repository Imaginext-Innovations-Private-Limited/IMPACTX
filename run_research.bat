@echo off
setlocal
cd /d "%~dp0"
set "RESEARCH_PY=..\Semantic_Research\.venv\Scripts\python.exe"
if not exist "%RESEARCH_PY%" (echo Research environment missing. This is optional and not needed to run ScamShield. & pause & exit /b 1)
if not exist "..\Semantic_Research\large_dataset_experiment\downloads" (echo Cached research datasets missing. No download or deployment will be attempted. & pause & exit /b 1)
"%RESEARCH_PY%" -c "import pyarrow, sklearn, httpx" >nul 2>nul
if errorlevel 1 (echo Research dependencies missing. Install pyarrow and project requirements in the research environment. & pause & exit /b 1)
"%RESEARCH_PY%" benchmark\research\external\train_mixed_research.py --ensemble
set "RESULT=%errorlevel%"
echo Research exit code: %RESULT%. No production changes made.
pause
exit /b %RESULT%
