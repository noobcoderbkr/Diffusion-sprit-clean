@echo off
powershell -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\run_flutter.ps1" %*
