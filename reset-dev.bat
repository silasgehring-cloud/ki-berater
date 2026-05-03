@echo off
setlocal

REM Hard-Reset: Stoppt alles + loescht Volumes (Postgres-Daten, Redis-Daten,
REM Qdrant-Daten). Danach hat der naechste start-dev.bat eine frische DB.
REM
REM Brauchst du wenn:
REM   - DB-Schema kaputt nach fehlerhafter Migration
REM   - Test-Daten weg-werfen vor neuem Test-Lauf
REM   - "irgendwas in Docker laeuft komisch"

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - HARD RESET (Daten weg!)
echo ============================================
echo.
echo Das loescht ALLE lokalen Daten:
echo   - Postgres ^(shops, conversations, products, ...^)
echo   - Redis-Cache
echo   - Qdrant-Vektoren
echo.

set /p CONFIRM=Wirklich ALLES loeschen [j/N]?
if /i not "%CONFIRM%"=="j" (
    echo Abgebrochen.
    pause
    exit /b 0
)

where docker 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Docker nicht im PATH.
    pause
    exit /b 1
)

echo.
echo --- docker compose down -v (loescht Volumes) ---
docker compose down -v
if errorlevel 1 (
    echo FEHLER beim docker compose down.
    pause
    exit /b 1
)

echo.
echo --- Loesche .local-shop ^(falls vorhanden^) ---
if exist .local-shop (
    del .local-shop
    echo .local-shop geloescht.
) else (
    echo .local-shop nicht vorhanden.
)

echo.
echo Reset komplett. Naechster start-dev.bat startet mit frischer DB.
echo.
pause
