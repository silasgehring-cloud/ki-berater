# Lokales Dev-Setup

Quick-Start fuer eigene Entwicklung + manuellen Test.
**Kein Docker noetig** — embedded Postgres via `pgserver`,
In-Memory Qdrant + Rate-Limit.

---

## Voraussetzungen

| Tool | Wofuer | Installation |
|---|---|---|
| **Python 3.12** | Backend | https://www.python.org/downloads/ (oder `winget install Python.Python.3.12`) |
| **Local von Flywheel** | WordPress + WC zum Testen | https://localwp.com/ |
| **Git** | Versionskontrolle | https://git-scm.com/download/win |
| **Google AI Studio Key** | Echte LLM-Antworten | https://aistudio.google.com/ — gratis |

Optional:
- **Visual Studio Code** mit Python + PHP-Extensions
- **TablePlus** / pgAdmin fuer Postgres-Inspection

---

## Backend hochfahren

**Doppelklick auf `start-dev.bat`** im Projekt-Root. Das macht alles:
1. `.env` aus `.env.example` kopieren falls fehlt
2. `ADMIN_API_KEY` auto-generieren falls leer
3. Embedded Postgres bootet (erstes Mal: ~50 MB Binary-Download)
4. Alembic-Migrationen laufen
5. uvicorn startet auf `http://localhost:8000`

Daten persistieren in `.pgsrv/` (gitignored). Ctrl+C im Fenster beendet
alles sauber.

Manuell ohne Bat-Datei:
```bash
cd D:/Cloude/WCommerce
.venv/Scripts/python.exe scripts/dev_server.py
```

Verifikation in einem zweiten Terminal:
```bash
curl http://localhost:8000/health     # → {"status":"ok"}
curl http://localhost:8000/ready      # → Postgres+Qdrant ok, Redis "skipped"
```

---

## Test-Shop anlegen

In einem neuen Git-Bash-Terminal (Backend laeuft weiter):

```bash
cd D:/Cloude/WCommerce
bash scripts/create-test-shop.sh
```

Skript liest `ADMIN_API_KEY` aus `.env`, fragt nach Shop-Domain, legt
Shop an und schreibt API-Key + Webhook-Secret in `.local-shop` (gitignored).

---

## Plugin in WordPress einbinden

1. Local von Flywheel: Site provisionieren (PHP 8.2 / nginx / MySQL Preferred)
2. Doppelklick auf `link-plugin-to-wp.bat` → Site-Name eingeben
3. WP-Admin → Plugins → "KI-Verkaufsberater" aktivieren
4. Settings unter "Einstellungen → KI-Berater":
   - Backend-URL: `http://localhost:8000`
   - API-Key + Webhook-Secret aus `.local-shop` einfuegen
   - Speichern → "Verbindung testen" klicken

Aenderungen im Plugin-Code in `D:/Cloude/WCommerce/plugin/ki-berater/`
sind sofort live im Browser (Junction → Refresh reicht).

---

## Reset / Aufraeumen

| Zweck | Befehl |
|---|---|
| Backend stoppen | Ctrl+C im start-dev-Fenster |
| Datenbank wegwerfen + neu starten | Doppelklick `reset-dev.bat` |
| Cache-/Log-Dateien aufraeumen | `rm -rf .ruff_cache .mypy_cache .pytest_cache` |

---

## Tests laufen lassen

```bash
.venv/Scripts/pytest.exe -v        # alle 182 Tests
.venv/Scripts/ruff.exe check backend
.venv/Scripts/mypy.exe backend
```

Tests booten ihr eigenes pgserver — `start-dev.bat` muss nicht laufen.

---

## Postgres direkt anschauen

`pgserver` hat keinen `psql`-Wrapper. Verbindungs-URL aus dem
`start-dev.bat`-Fenster ablesen (Format `127.0.0.1:PORT/postgres`),
dann mit beliebigem Postgres-Client (TablePlus, pgAdmin, DBeaver) verbinden:

- Host: `127.0.0.1`
- Port: aus dem Log
- DB:   `postgres`
- User: `postgres`
- Password: leer

Beispiel-Queries:
```sql
SELECT count(*) FROM products;
SELECT id, domain, plan FROM shops;
SELECT shop_id, model, sum(cost_eur) FROM llm_usage GROUP BY 1,2;
SELECT * FROM product_clicks ORDER BY clicked_at DESC LIMIT 10;
```

---

## Haeufige Stolpersteine

**`start-dev.bat` haengt bei "Boote embedded Postgres"**
→ Erster Run laedt ~50 MB Binaries herunter. Bei langsamer Internetverbindung
kann das mehrere Minuten dauern. Im Hintergrund laeuft `pgserver` weiter.

**`/ready` zeigt Redis als "skipped"**
→ Korrekt — wir nutzen In-Memory-Rate-Limit im Dev-Mode.

**Backend startet, aber `/ready` zeigt Postgres als "fail"**
→ pgserver konnte nicht starten. `reset-dev.bat` ausfuehren um `.pgsrv/`
zu loeschen, dann `start-dev.bat` neu.

**Plugin-Verbindungstest in WP "Auth fehlgeschlagen"**
→ API-Key falsch eingegeben. Vergleichen mit `.local-shop`.

**Plugin-Verbindungstest "CORS-Error"**
→ Shop-Domain im POST `/v1/shops`-Call passt nicht zur Local-Site-Domain.
Test-Shop neu anlegen mit korrekter Domain.

**Chat antwortet nicht**
→ Backend-Logs (im `start-dev`-Fenster) checken. Ohne `GOOGLE_API_KEY` /
`ANTHROPIC_API_KEY` in `.env` faellt der Backend auf den Mock-Provider
zurueck — du siehst dann eine immer-gleiche Beispielantwort. Fuer echte
Antworten: API-Key in `.env`, dann Backend neu starten.

---

## Was nach dem lokalen Test kommt

Siehe [DEPLOY.md](DEPLOY.md) fuer Hetzner-Cloud-Deployment der
Production-Variante (dort wird Docker fuer Multi-Container-Deployment
verwendet — lokal nicht noetig). [BILLING_SETUP.md](BILLING_SETUP.md)
fuer Stripe-Konfiguration, [PLUGIN_DISTRIBUTION.md](PLUGIN_DISTRIBUTION.md)
fuer GitHub-Releases als Update-Server.
