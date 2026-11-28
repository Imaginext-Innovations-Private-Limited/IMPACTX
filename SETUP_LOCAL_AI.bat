@echo off
setlocal
cd /d "%~dp0"
where ollama >nul 2>nul
if errorlevel 1 (
 echo Install Ollama from https://ollama.com/download/windows and reopen this file.
 pause
 exit /b 1
)
set OLLAMA_NO_CLOUD=1
ollama pull qwen2.5:3b
if errorlevel 1 goto failed
ollama pull bge-m3
if errorlevel 1 goto failed
echo Open Admin - Knowledge base - Build / refresh embeddings. Wait for completion in Agent monitor.
pause
exit /b 0
:failed
echo Open the Ollama desktop app, check free disk space and Internet, then retry.
pause
exit /b 1
