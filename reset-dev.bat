@echo off
setlocal

REM Hard-Reset: Loescht .pgsrv/ (Postgres-Daten) und .local-shop.
REM Naechster start-dev.bat startet mit frischer DB.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - HARD RESET (Daten weg!)
echo ============================================
echo.
echo Das loescht:
echo   - .pgsrv\        (alle Postgres-Daten: shops, conversations, products)
echo   - .local-shop    (gespeicherter Test-Shop-API-Key)
echo.
echo NICHT geloescht:
echo   - .env           (deine Konfiguration)
echo   - venv/Plugin    (Code bleibt)
echo.

set /p CONFIRM=Wirklich ALLES loeschen [j/N]?
if /i not "%CONFIRM%"=="j" (
    echo Abgebrochen.
    pause
    exit /b 0
)

echo.
echo Stelle sicher dass start-dev.bat nicht mehr laeuft ^(Ctrl+C dort^).
echo.
timeout /t 2 /nobreak >NUL

if exist .pgsrv (
    echo Loesche .pgsrv\ ...
    rmdir /S /Q .pgsrv
    echo OK
) else (
    echo .pgsrv\ nicht vorhanden, ueberspringe.
)

if exist .local-shop (
    echo Loesche .local-shop ...
    del .local-shop
    echo OK
) else (
    echo .local-shop nicht vorhanden, ueberspringe.
)

echo.
echo Reset komplett. Naechster start-dev.bat startet mit frischer DB.
echo.
pause
