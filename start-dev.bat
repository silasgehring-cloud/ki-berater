@echo off
setlocal EnableDelayedExpansion

REM Doppelklick: Backend-Dev-Stack hochfahren.
REM Docker-Services laufen detached, Backend (uvicorn) im Vordergrund.
REM Ctrl+C stoppt nur uvicorn -- Docker laeuft weiter.
REM Zum kompletten Stop: stop-dev.bat doppelklicken.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Dev-Backend hochfahren
echo ============================================
echo.

REM Docker installiert?
where docker 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Docker nicht im PATH.
    echo.
    echo Installiere Docker Desktop:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

REM Docker Daemon laeuft?
docker info 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Docker Daemon laeuft nicht.
    echo.
    echo Starte Docker Desktop, warte bis das Tray-Icon stabil ist
    echo ^(nicht mehr animiert^), dann doppelklicke diese Datei nochmal.
    echo.
    pause
    exit /b 1
)

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
echo --- Starte Docker-Services ^(Postgres + Redis + Qdrant^) ---
docker compose up -d
if errorlevel 1 (
    echo FEHLER beim docker compose up.
    pause
    exit /b 1
)

echo.
echo --- Warte auf Postgres ^(max 30s^) ---
set TRIES=0
:WAIT_PG
set /a TRIES+=1
docker compose exec -T postgres pg_isready -U ki 1>NUL 2>NUL
if not errorlevel 1 goto PG_READY
if !TRIES! GEQ 30 (
    echo FEHLER: Postgres nicht ready nach 30s.
    echo Logs anschauen mit: tail-logs.bat
    pause
    exit /b 1
)
timeout /t 1 /nobreak >NUL
goto WAIT_PG

:PG_READY
echo Postgres ready.
echo.

echo --- Datenbank-Migration ^(alembic upgrade head^) ---
pushd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
set MIGRATE_RC=!errorlevel!
popd
if not !MIGRATE_RC!==0 (
    echo FEHLER beim alembic upgrade.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Backend startet auf http://localhost:8000
echo ============================================
echo.
echo Logs erscheinen unten. Ctrl+C stoppt uvicorn.
echo Docker-Services laufen weiter -- separater Stop mit stop-dev.bat.
echo Test-Shop anlegen: bash scripts/create-test-shop.sh
echo.

.venv\Scripts\uvicorn.exe backend.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo Backend gestoppt. Docker-Services laufen weiter.
echo Komplett-Stop: stop-dev.bat
pause
