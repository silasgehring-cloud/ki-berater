@echo off
setlocal

REM Doppelklick: Test-Shop anlegen via Backend-Admin-Endpoint.
REM Liest ADMIN_API_KEY aus .env, fragt nach Domain, schreibt
REM API-Key + Webhook-Secret in .local-shop zum Copy-Paste.
REM
REM Voraussetzung: start-dev.bat laeuft (Backend auf :8000).

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Test-Shop anlegen
echo ============================================
echo.

if not exist .venv\Scripts\python.exe (
    echo FEHLER: .venv nicht gefunden.
    echo Setup zuerst:
    echo   py -3.12 -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev]"
    pause
    exit /b 1
)

if not exist .env (
    echo FEHLER: .env fehlt. Starte erst start-dev.bat ^(legt .env an^).
    pause
    exit /b 1
)

.venv\Scripts\python.exe scripts\create_test_shop.py
set RC=%errorlevel%

echo.
if %RC%==0 (
    echo Naechster Schritt: start-demo.bat doppelklicken.
) else (
    echo Fehler aufgetreten ^(Exit-Code %RC%^).
)
pause
