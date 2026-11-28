@echo off
setlocal
title MINDMATE - Student Wellbeing Companion
cd /d "%~dp0"

echo ======================================================
echo   MINDMATE - Student Wellbeing Companion
echo ======================================================
echo.

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example
  )
)

if not exist "node_modules" (
  echo Dependencies are not installed.
  echo Please run: npm.cmd install --legacy-peer-deps
  echo.
  pause
  exit /b 1
)

echo Starting the existing full-stack TypeScript server...
echo Keep this window open while using MINDMATE.
echo When the server says it is running, open http://localhost:3000
echo.
call npm.cmd run dev
pause
