@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Please complete the Python setup in README.md first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0region_compositor.py"
