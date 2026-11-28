@echo off
cd /d "%~dp0"
where tesseract >nul 2>nul
if errorlevel 1 if not exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" winget install --id UB-Mannheim.TesseractOCR -e
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $d='local_data/ocr-languages'; New-Item -ItemType Directory -Force $d | Out-Null; foreach ($l in 'eng','tel','hin','kan') { $f=Join-Path $d ($l+'.traineddata'); Invoke-WebRequest ('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/'+$l+'.traineddata') -OutFile ($f+'.part'); Move-Item -Force ($f+'.part') $f }; Write-Host 'Language files installed.'"
pause
