@echo off
setlocal

REM Stoppt Docker-Services (Postgres + Redis + Qdrant).
REM Daten bleiben erhalten -- naechster start-dev.bat startet wo wir aufgehoert haben.
REM Fuer kompletten Reset (Volumes loeschen): reset-dev.bat.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Dev-Backend stoppen
echo ============================================
echo.

where docker 1>NUL 2>NUL
if errorlevel 1 (
    echo Docker nicht im PATH -- nichts zu stoppen.
    pause
    exit /b 0
)

echo --- docker compose down ---
docker compose down
if errorlevel 1 (
    echo FEHLER beim docker compose down.
    pause
    exit /b 1
)

echo.
echo Alle Dev-Services gestoppt. Daten in Volumes bleiben erhalten.
echo Naechster Start: start-dev.bat
echo.
pause
