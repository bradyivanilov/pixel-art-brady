@echo off
REM Hermes Pixel Office - launcher
REM Starts the local server and opens the office in your browser.

setlocal
cd /d "%~dp0"

set PY="python"
if exist "C:\Users\%USERNAME%\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" set PY="C:\Users\%USERNAME%\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

echo Starting Hermes Pixel Office...
start "" http://localhost:8770
%PY% server.py

echo.
echo Server stopped.
pause
