@echo off
setlocal

REM Doppelklick: Demo-Shop auf http://localhost:5000 starten.
REM
REM Erwartet:
REM   1. Backend laeuft (start-dev.bat) auf http://localhost:8000
REM   2. .local-shop existiert (bash scripts/create-test-shop.sh)
REM
REM Generiert demo/config.js automatisch aus .local-shop und startet
REM dann einen Python-HTTP-Server auf Port 5000.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Demo-Shop starten
echo ============================================
echo.

if not exist .venv\Scripts\python.exe (
    echo FEHLER: .venv nicht gefunden.
    pause
    exit /b 1
)

if not exist .local-shop (
    echo FEHLER: .local-shop nicht gefunden.
    echo.
    echo Erst einen Test-Shop anlegen:
    echo   1. start-dev.bat starten ^(Backend^)
    echo   2. In neuem Terminal: bash scripts/create-test-shop.sh
    echo.
    pause
    exit /b 1
)

echo --- Demo-Konfig generieren ---
.venv\Scripts\python.exe scripts\generate_demo_config.py
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Demo laeuft auf http://localhost:5000
echo ============================================
echo.
echo Oeffne im Browser: http://localhost:5000
echo Ctrl+C beendet den Server.
echo.

cd demo
..\.venv\Scripts\python.exe -m http.server 5000

pause
