@echo off
setlocal EnableDelayedExpansion

REM Erstellt einen Junction von der Local-WP-Plugins-Folder zur lokalen
REM Plugin-Source. Aenderungen am Code werden sofort live im Browser.

cd /d "%~dp0"

echo ============================================
echo   KI-Berater - Plugin-Symlink ins Local-WP
echo ============================================
echo.

set "PLUGIN_SRC=%~dp0plugin\ki-berater"

if not exist "%PLUGIN_SRC%" (
    echo FEHLER: Plugin-Quelle nicht gefunden:
    echo %PLUGIN_SRC%
    pause
    exit /b 1
)

echo Plugin-Quelle: %PLUGIN_SRC%
echo.

if not exist "%USERPROFILE%\Local Sites" (
    echo FEHLER: "Local Sites"-Ordner nicht gefunden unter:
    echo %USERPROFILE%\Local Sites
    echo.
    echo Stelle sicher dass Local von Flywheel installiert ist und mindestens
    echo eine Site provisioniert hat.
    pause
    exit /b 1
)

echo Verfuegbare Local-Sites:
echo --------------------------
dir /b /ad "%USERPROFILE%\Local Sites" 2>NUL
echo --------------------------
echo.

set /p SITE_NAME=Local-Site-Name eingeben:

if "!SITE_NAME!"=="" (
    echo Kein Name eingegeben. Abgebrochen.
    pause
    exit /b 1
)

set "TARGET_DIR=%USERPROFILE%\Local Sites\!SITE_NAME!\app\public\wp-content\plugins"

if not exist "!TARGET_DIR!" (
    echo FEHLER: Plugin-Ordner nicht gefunden unter:
    echo !TARGET_DIR!
    echo.
    echo Pruefe den Site-Namen und ob die Site gestartet wurde.
    pause
    exit /b 1
)

set "LINK_PATH=!TARGET_DIR!\ki-berater"

if exist "!LINK_PATH!" (
    echo.
    echo Verzeichnis existiert bereits:
    echo !LINK_PATH!
    echo.
    set /p OVERWRITE=Loeschen und Symlink anlegen? [j/N]
    if /i not "!OVERWRITE!"=="j" (
        echo Abgebrochen.
        pause
        exit /b 0
    )
    rmdir /S /Q "!LINK_PATH!" 2>NUL
    del "!LINK_PATH!" 2>NUL
)

mklink /J "!LINK_PATH!" "%PLUGIN_SRC%"
if errorlevel 1 (
    echo.
    echo FEHLER beim Erstellen des Junctions.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   FERTIG!
echo ============================================
echo.
echo Junction angelegt:
echo   !LINK_PATH!
echo   --^> %PLUGIN_SRC%
echo.
echo Naechste Schritte:
echo   1. In Local: "WP Admin"-Button klicken
echo   2. WP-Sidebar: Plugins
echo   3. "KI-Verkaufsberater" Aktivieren
echo   4. Code-Aenderungen in D:\Cloude\WCommerce\plugin\ki-berater
echo      werden sofort live - nur Browser-Refresh noetig.
echo.
pause
