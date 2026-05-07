@echo off
REM Doppelklick: WordPress-Plugin als ZIP fuer die Verteilung packen.
REM Output landet in dist\ki-berater-vX.Y.Z.zip
REM
REM Funktioniert ohne composer/php — die ZIP ist dann allerdings ohne vendor/,
REM d.h. der Auto-Update-Mechanismus im WP ist aus. Plugin laeuft trotzdem.
REM Wer composer hat (winget install Composer.Composer), bekommt die volle ZIP.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-plugin.ps1"
set RC=%errorlevel%

echo.
if "%RC%"=="0" (
    echo Done.
) else (
    echo Build fehlgeschlagen mit Exit-Code %RC%.
)
pause
exit /b %RC%
