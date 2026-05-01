# Plugin-Distribution via GitHub-Releases

Wir distributieren das Plugin **NICHT** über das WordPress.org Plugin Directory
(zumindest nicht zum Pilot-Launch). Stattdessen: GitHub-Releases als
Update-Server. Shop-Betreiber bekommen ein WordPress-Update-Notification wie
bei jedem WP.org-Plugin — wir behalten aber volle Kontrolle und müssen keinen
WP.org-Review durchlaufen.

**Aktueller Repo:** [`silasgehring-cloud/ki-berater`](https://github.com/silasgehring-cloud/ki-berater)
(Monorepo: Backend + Plugin + Landing-Page + CI in einem Repo)

---

## Architektur

```
GitHub Repo (silasgehring-cloud/ki-berater)
   └── Releases (mit zip-Asset)
        ↑ poll alle 12h
WordPress-Backend (im Shop)
   └── Plugin Update Checker (PUC v5)
        ├── liest plugin-header `Version:` lokal
        ├── vergleicht mit Latest Release Tag
        └── zeigt Update wenn neuer
```

---

## ENTSCHEIDUNG: public vs. private Repo

### Empfehlung: **public** (Standard für GPL-Plugins)

| | public | private + PAT |
|---|---|---|
| Plugin-Code öffentlich? | Ja | Nein |
| PAT in jeder Shop-WP nötig? | Nein | **Ja** |
| Onboarding-UX | 1-Click | PAT-Constant in wp-config.php |
| Sicherheits-Risiko | keiner | PAT-Leak via WP-DB-Backup, Shop-Hack |
| GPL-konform? | ✅ | ⚠️ (Source-Distribution-Pflicht steht trotzdem im Plugin-Code) |
| WP.org-Submission später möglich? | direkt | erst nach Public-Schaltung |

**Plugin-Code ist GPL-2.0 (WordPress-Pflicht).** Wer das Plugin installiert,
hat sowieso Anspruch auf den Source. Der "Wettbewerbsvorteil" eines KI-Berater-
SaaS ist das Backend-Service + LLM-Routing + Pilot-Daten — nicht der
Plugin-Code, der eigentlich nur HTTP-Calls macht.

→ **`silasgehring-cloud/ki-berater` von Private auf Public umschalten** im
GitHub-Repo-Settings → Danger Zone → "Change repository visibility".

Falls du **private bleiben willst**, siehe Sektion "Private Repo Setup" weiter
unten.

---

## Erst-Setup (einmalig)

### 1. Code in den Repo pushen

```bash
cd D:/Cloude/WCommerce

git init
git branch -M main
git add .
git commit -m "Initial: Backend + Plugin + Landing + Production-Setup"

git remote add origin https://github.com/silasgehring-cloud/ki-berater.git
git push -u origin main
```

`.gitignore` ist so konfiguriert dass nur Source-Files gepusht werden:
- `plugin/ki-berater/vendor/` ist excluded (wird per CI installiert)
- `landing/node_modules/`, `landing/dist/` excluded
- `.env`, `.venv/` excluded
- `postgres_data/`, `qdrant_data/` excluded

### 2. Erstes Plugin-Release taggen

```bash
git tag plugin-v0.1.0
git push --tags
```

Die GitHub-Action [`.github/workflows/release-plugin.yml`](.github/workflows/release-plugin.yml)
läuft automatisch:
1. `composer install --no-dev --optimize-autoloader` — installiert PUC + Runtime-Deps in `vendor/`
2. `rsync` baut sauberes Plugin-Verzeichnis ohne Dev-Dateien
3. `zip -r ki-berater-plugin-v0.1.0.zip ki-berater`
4. `softprops/action-gh-release` erstellt Release + hängt zip an

Nach ~2 Min: https://github.com/silasgehring-cloud/ki-berater/releases/tag/plugin-v0.1.0

---

## Release-Workflow (jedes Mal)

### Version bumpen — drei Stellen müssen synchron sein

```bash
# 1. plugin/ki-berater/ki-berater.php — Plugin-Header
#    * Version: 0.2.0
# 2. plugin/ki-berater/ki-berater.php — KIB_VERSION-Konstante
#    const KIB_VERSION = '0.2.0';
# 3. plugin/ki-berater/readme.txt — Stable tag:
#    Stable tag: 0.2.0
```

### Tag pushen

```bash
git add plugin/ki-berater/ki-berater.php plugin/ki-berater/readme.txt
git commit -m "Plugin v0.2.0: Click-Tracking + Strict-Attribution"
git push

git tag plugin-v0.2.0
git push --tags
```

### WordPress-Endkunden bekommen automatisch das Update

PUC pollt alle 12 Stunden. Im WP-Admin erscheint "Update available" mit
"Update now"-Button. Force-Check via "Check Again" im Plugins-Listing.

---

## Lokal testen vor Tag

```bash
make plugin-zip
# → dist/ki-berater.zip

# In WP installieren via "Plugins → Add New → Upload Plugin"
```

So weißt du vor dem Tag-Push, dass die Datei wirklich installierbar ist
und PUC nicht crasht.

---

## Erste Installation beim Shop-Betreiber

Beim allerersten Mal kann WordPress das Plugin nicht von GitHub abrufen
(es ist ja noch nicht installiert). Drei Wege:

### A) Direkter Zip-Download (am einfachsten)

```
https://github.com/silasgehring-cloud/ki-berater/releases/latest
→ "ki-berater-plugin-v0.x.y.zip" herunterladen
WP-Admin → Plugins → "Plugin hochladen" → zip auswählen → Aktivieren
```

### B) WP-CLI (für Profis)

```bash
wp plugin install \
  https://github.com/silasgehring-cloud/ki-berater/releases/download/plugin-v0.1.0/ki-berater-plugin-v0.1.0.zip \
  --activate
```

### C) "Install from URL"-Plugin

Helper-Plugins wie "Easy Plugins from GitHub" — für Pilot-Akquise zu viel
Aufwand. A) reicht.

---

## Private Repo Setup (falls du dabei bleiben willst)

### 1. Fine-grained Personal Access Token erstellen

GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens**

- **Token name:** `ki-berater-plugin-readonly-{shop-name}` (pro Shop separat)
- **Resource owner:** silasgehring-cloud
- **Repository access:** Only select repositories → `ki-berater`
- **Permissions:** Repository permissions → **Contents: Read-only**
- **Expiration:** 1 Jahr (rotiere danach)

### 2. PAT auf der Shop-WordPress-Instanz hinterlegen

In `wp-config.php` des Shops:

```php
// Plugin-Update-Checker für privates Repo
define('KIB_UPDATE_CHECKER_TOKEN', 'github_pat_11ABCDEF...');
```

### 3. Risiko-Bewusstsein

- **Token ist im Klartext in wp-config.php.** Wer den Server hackt, sieht ihn.
- **Token ist im DB-Backup**, falls jemand `wp-config.php` mitsichern lässt.
- **Token rotieren** bei jedem Verdacht. Sofortige Wirkung dank fine-grained
  scope: alter Token wird invalid, neuer Token muss in alle Shops.
- **Nicht für Mehr-Shop-Pilot geeignet.** Ein PAT pro Shop = N×Rotation-Aufwand.

→ Bei **>3 Shops im Pilot:** Repo public schalten. Lebenszeit-ROI deutlich
besser.

---

## Häufige Fallstricke

**"Update kommt nicht an obwohl ich getaggt habe"**
- WordPress-Plugin-Cache: `wp transient delete --all` oder im Admin auf
  "Check Again" im Plugins-Listing klicken
- PUC pollt frühestens alle 12h. Force: `?puc_check_for_updates=1` an URL.

**"Update bricht ab bei Composer-Autoload-Fehler"**
- Verifiziere in `dist/ki-berater.zip` dass `vendor/autoload.php` enthalten ist
- Composer-PHP-Version muss zur Runtime-PHP-Version passen (>=8.0)

**"GitHub-Action schlägt fehl mit Permission denied"**
- Repo-Settings → Actions → Workflow permissions: **Read and write permissions**
  aktivieren (sonst kann `softprops/action-gh-release` nicht Release erstellen)

**"PUC zeigt 'API rate limit exceeded'"** (private Repo)
- PAT abgelaufen oder falsch konfiguriert
- Anonymous-Limit ist 60/h pro IP, mit PAT 5000/h pro Account → praktisch
  unbegrenzt für unsere Polling-Frequenz

---

## Versionierungs-Konvention

Tags: `plugin-vMAJOR.MINOR.PATCH` (semantic versioning).

| Bump-Art | Wann |
|---|---|
| MAJOR | Breaking changes (z.B. Backend-API-Vertrag ändert sich) |
| MINOR | Neue Features (z.B. neuer Settings-Schalter) |
| PATCH | Bugfixes ohne Feature-Änderungen |

Backend-Versionen (`KIB_VERSION` im Plugin matcht aktuelles Backend) und
Plugin-Versionen können separat laufen — der Plugin-Header `Requires Backend:`
existiert nicht, aber wir prüfen API-Compat über das `/version`-Endpoint
beim "Verbindung testen"-Button.
