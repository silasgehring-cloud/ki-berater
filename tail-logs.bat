@echo off
setlocal

REM Live-Tail aller Docker-Container-Logs (Postgres + Redis + Qdrant).
REM Backend-Logs (uvicorn) erscheinen direkt im start-dev.bat-Fenster --
REM hier siehst du nur die Service-Logs.
REM Ctrl+C beendet den Tail (Container laufen weiter).

cd /d "%~dp0"

where docker 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Docker nicht im PATH.
    pause
    exit /b 1
)

echo ============================================
echo   KI-Berater - Docker-Service-Logs
echo ============================================
echo.
echo Live-Tail von Postgres + Redis + Qdrant.
echo Ctrl+C beendet den Tail ^(Services laufen weiter^).
echo.

docker compose logs -f --tail=100
