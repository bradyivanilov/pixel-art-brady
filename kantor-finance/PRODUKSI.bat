@echo off
REM Kantor Berita Finance - launcher
REM 1) pastikan server pixel office jalan (kalau belum, nyalakan)
REM 2) buka halaman kantor di browser

setlocal
cd /d "%~dp0"

set PY="python"
where python >nul 2>&1 && set PY="python"
if exist "C:\Users\%USERNAME%\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" set PY="C:\Users\%USERNAME%\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"

REM cek server pixel office (port 8770); kalau mati, nyalakan
powershell -NoProfile -Command "if(-not (Get-NetTCPConnection -LocalPort 8770 -State Listen -ErrorAction SilentlyContinue)){ exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo Menyalakan server pixel office...
  start "" /min cmd /c "cd /d %~dp0..\hermes-pixel-office && %PY% server.py"
  timeout /t 2 >nul
)

echo Membuka Kantor Berita Finance...
start "" http://localhost:8770/kantor

echo.
echo Pilih salah satu:
echo   [1] Produksi berita baru (topik dipilih otomatis dari feed)
echo   [2] Produksi berita dengan topik yang kamu tentukan
echo   [3] Keluar
echo.
set /p pilih="Pilihan (1/2/3): "

if "%pilih%"=="1" (
  %PY% engine.py
) else if "%pilih%"=="2" (
  set /p topik="Tulis topiknya: "
  %PY% engine.py --topik "%topik%"
) else (
  echo Selesai.
)

pause
