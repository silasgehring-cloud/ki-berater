@echo off
setlocal EnableDelayedExpansion

REM Doppelklick: Backend hochfahren OHNE Docker.
REM Embedded Postgres via pgserver, In-Memory Qdrant, In-Memory Rate-Limit.
REM Postgres-Daten persistieren in .pgsrv/ (gitignored).
REM
REM Stop: Ctrl+C in diesem Fenster.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Dev-Backend hochfahren
echo ============================================
echo.

REM .venv vorhanden?
if not exist .venv\Scripts\python.exe (
    echo FEHLER: .venv nicht gefunden.
    echo.
    echo Setup laufen lassen:
    echo   py -3.12 -m venv .venv
    echo   .venv\Scripts\pip install -e ".[dev]"
    echo.
    pause
    exit /b 1
)

REM .env vorhanden?
if not exist .env (
    echo .env nicht vorhanden, erstelle aus .env.example...
    copy /Y .env.example .env >NUL
    echo.
    echo HINWEIS: Trage GOOGLE_API_KEY in .env ein fuer echte LLM-Antworten.
    echo Ohne Key: Mock-Provider liefert statische Demo-Antworten.
    echo.
)

REM ADMIN_API_KEY auto-generieren wenn leer
.venv\Scripts\python.exe scripts\ensure-admin-key.py
if errorlevel 1 (
    echo FEHLER beim ADMIN_API_KEY-Setup.
    pause
    exit /b 1
)

echo.
.venv\Scripts\python.exe scripts\dev_server.py
set RC=!errorlevel!

echo.
if !RC!==0 (
    echo Backend sauber gestoppt.
) else (
    echo Backend mit Exit-Code !RC! beendet.
)
pause
