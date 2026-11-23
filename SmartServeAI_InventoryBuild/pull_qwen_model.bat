@echo off
echo Pulling the SmartServe AI default model: qwen2.5:0.5b
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install it from https://ollama.com and run this file again.
  pause
  exit /b 1
)
ollama pull qwen2.5:0.5b
if errorlevel 1 (
  echo Model download failed. Check your internet connection and Ollama installation.
  pause
  exit /b 1
)
echo Qwen 2.5 0.5B is ready. Start SmartServe AI with run_smartserve.bat.
pause
