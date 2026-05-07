<#
    Plugin-ZIP-Builder fuer KI-Berater (WordPress).

    Was passiert:
      1. Liest Version aus plugin/ki-berater/ki-berater.php (Header "Version: x.y.z")
      2. Kopiert plugin/ki-berater/ nach dist/staging/ki-berater/
      3. Loescht alle Eintraege aus .distignore (composer*, tests/, etc.)
      4. Falls composer auf PATH: composer install --no-dev (zieht plugin-update-checker)
      5. Packt dist/ki-berater-vX.Y.Z.zip
      6. Loescht das Staging-Verzeichnis

    Wenn composer fehlt, wird die ZIP trotzdem gebaut. Das Plugin laeuft in WP,
    nur der Auto-Update-Mechanismus ist dann aus (siehe class-update-checker.php
    Zeile 53-57: skip-bei-fehlendem-vendor).
#>

$ErrorActionPreference = 'Stop'

# Repo-Root = Parent von /scripts/
$Root = Split-Path -Parent $PSScriptRoot
$PluginSrc = Join-Path $Root 'plugin\ki-berater'
$Dist = Join-Path $Root 'dist'
$Staging = Join-Path $Dist 'staging\ki-berater'

if (-not (Test-Path $PluginSrc)) {
    Write-Error "Plugin-Quelle nicht gefunden: $PluginSrc"
}

# 1) Version auslesen
$mainPhp = Join-Path $PluginSrc 'ki-berater.php'
$header = Get-Content $mainPhp -Raw -Encoding UTF8
if ($header -notmatch '(?m)^\s*\*\s*Version:\s+([\d\.]+)') {
    Write-Error "Konnte Version aus ki-berater.php nicht lesen."
}
$Version = $Matches[1]
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Building ki-berater plugin v$Version" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 2) Staging vorbereiten
if (Test-Path $Staging) {
    Remove-Item -Recurse -Force $Staging
}
New-Item -ItemType Directory -Force -Path $Staging | Out-Null
Copy-Item -Recurse -Force "$PluginSrc\*" $Staging

# 3) .distignore anwenden
$distIgnore = Join-Path $Staging '.distignore'
if (Test-Path $distIgnore) {
    # Erst komplett lesen, dann iterieren - sonst haelt Get-Content den File-Handle waehrend
    # wir versuchen, .distignore selbst zu loeschen.
    $patterns = @(Get-Content $distIgnore -Encoding UTF8 |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith('#') })
    foreach ($raw in $patterns) {
        $pattern = $raw.TrimEnd('/').TrimEnd('\')
        $target = Join-Path $Staging $pattern
        if (Test-Path $target) {
            Remove-Item -Recurse -Force $target
            Write-Host "  - removed $pattern" -ForegroundColor DarkGray
        }
    }
}

# 4) composer (optional)
$composer = Get-Command composer -ErrorAction SilentlyContinue
if ($composer -and (Test-Path (Join-Path $PluginSrc 'composer.json'))) {
    Write-Host "  + composer install --no-dev" -ForegroundColor Green
    # composer braucht composer.json/lock - diese wurden vom .distignore entfernt; kurz zurueckkopieren
    Copy-Item -Force (Join-Path $PluginSrc 'composer.json') $Staging
    if (Test-Path (Join-Path $PluginSrc 'composer.lock')) {
        Copy-Item -Force (Join-Path $PluginSrc 'composer.lock') $Staging
    }
    Push-Location $Staging
    try {
        & composer install --no-dev --optimize-autoloader --no-interaction --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "composer install fehlgeschlagen (Exit $LASTEXITCODE) - vendor/ fehlt, Auto-Update wird im WP deaktiviert sein."
        }
    } finally {
        Pop-Location
        # composer-Files nach dem Install wieder weg - landen sonst im Zip
        Remove-Item -Force (Join-Path $Staging 'composer.json') -ErrorAction SilentlyContinue
        Remove-Item -Force (Join-Path $Staging 'composer.lock') -ErrorAction SilentlyContinue
    }
} else {
    if (-not $composer) {
        Write-Warning "composer nicht auf PATH - vendor/ wird NICHT gebaut. Auto-Update im WP ist deaktiviert. Plugin laeuft trotzdem."
    }
}

# 5) Zippen
$zipName = "ki-berater-v$Version.zip"
$zipPath = Join-Path $Dist $zipName
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

# Compress-Archive: Quelle muss ki-berater/ sein, nicht der Inhalt - sonst entpackt WP es flach.
$stagingParent = Split-Path -Parent $Staging
Compress-Archive -Path $Staging -DestinationPath $zipPath -CompressionLevel Optimal

# 6) Cleanup
Remove-Item -Recurse -Force $stagingParent

$size = "{0:N1}" -f ((Get-Item $zipPath).Length / 1KB)
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  OK -> $zipPath" -ForegroundColor Green
Write-Host "  Groesse: $size KB" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
