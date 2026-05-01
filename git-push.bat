@echo off
setlocal EnableDelayedExpansion

REM Quick-push helper. Doppelklick: zeigt Aenderungen, fragt Commit-Message,
REM committet und pusht. Pause am Ende - Fenster bleibt offen.

cd /d "%~dp0"

echo ============================================
echo   KI-Verkaufsberater - Git Push
echo ============================================
echo.

where git 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Git ist nicht im PATH.
    echo Installiere Git for Windows: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

git rev-parse --git-dir 1>NUL 2>NUL
if errorlevel 1 (
    echo FEHLER: Kein Git-Repo gefunden.
    echo Initialisiere zuerst mit: git init
    echo.
    pause
    exit /b 1
)

echo Branch:
git rev-parse --abbrev-ref HEAD
echo.

echo Aktuelle Aenderungen:
echo --------------------
git status --short
echo --------------------
echo.

set HAS_CHANGES=0
for /f %%i in ('git status --porcelain') do set HAS_CHANGES=1

if "!HAS_CHANGES!"=="0" (
    echo Keine lokalen Aenderungen zu committen.
    echo.
    set /p PUSH_ANYWAY=Trotzdem nur pushen [j/N]?
    if /i not "!PUSH_ANYWAY!"=="j" (
        echo Abgebrochen.
        echo.
        pause
        exit /b 0
    )
    goto PUSH_ONLY
)

echo Commit-Message eingeben [leer = Auto-Default mit Datum/Uhrzeit]:
set /p COMMIT_MSG=^>^>^>

if "!COMMIT_MSG!"=="" set COMMIT_MSG=Update %date% %time%

echo.
echo --- git add . ---
git add .
if errorlevel 1 (
    echo.
    echo FEHLER beim Staging.
    pause
    exit /b 1
)

echo.
echo --- git commit ---
git commit -m "!COMMIT_MSG!"

:PUSH_ONLY
echo.
echo --- git push ---
git push
if errorlevel 1 (
    echo.
    echo ============================================
    echo   PUSH FEHLGESCHLAGEN
    echo ============================================
    echo Moegliche Ursachen:
    echo   1. Keine Internetverbindung
    echo   2. GitHub-Login abgelaufen
    echo   3. Branch noch nicht getrackt: git push -u origin main
    echo   4. Konflikt mit Remote: erst "git pull --rebase" ausfuehren
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   FERTIG - Push erfolgreich.
echo ============================================
echo.
git log --oneline -1
echo.
pause
