# Lokales Dev-Setup

Quick-Start fuer eigene Entwicklung + manuellen Test.

---

## Voraussetzungen

| Tool | Wofuer | Installation |
|---|---|---|
| **Python 3.12** | Backend | https://www.python.org/downloads/ (oder `winget install Python.Python.3.12`) |
| **Docker Desktop** | Postgres + Redis + Qdrant | https://www.docker.com/products/docker-desktop/ |
| **Local von Flywheel** | WordPress + WC zum Testen | https://localwp.com/ |
| **Git** | Versionskontrolle | https://git-scm.com/download/win |
| **Google AI Studio Key** | Echte LLM-Antworten | https://aistudio.google.com/ — gratis |

Optional aber empfohlen:
- **Visual Studio Code** mit Python + PHP-Extensions
- **TablePlus** o.ä. fuer Postgres-Inspection

---

## Backend hochfahren (5 Befehle)

```bash
cd D:/Cloude/WCommerce

# 1. .env aus Template
cp .env.example .env

# 2. ADMIN_API_KEY in .env eintragen — z.B. mit:
openssl rand -hex 32
# Output kopieren, in .env: ADMIN_API_KEY=<output>

# 3. Optional: GOOGLE_API_KEY in .env eintragen
# (ohne Key: Backend nutzt Mock-Provider als Dev-Fallback)

# 4. Services starten (Postgres + Redis + Qdrant)
docker compose up -d

# 5. DB-Schema migrieren
cd backend && alembic upgrade head && cd ..

# 6. Backend starten
.venv/Scripts/uvicorn.exe backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend laeuft auf http://localhost:8000

Verifikation:
```bash
curl http://localhost:8000/health     # → {"status":"ok"}
curl http://localhost:8000/ready      # → JSON mit Postgres/Redis/Qdrant-Status
```

---

## Test-Shop anlegen

In einem neuen Terminal (Backend laeuft weiter):

```bash
cd D:/Cloude/WCommerce
bash scripts/create-test-shop.sh
```

Skript liest `ADMIN_API_KEY` aus `.env`, fragt nach Shop-Domain, legt
Shop an und schreibt API-Key + Webhook-Secret in `.local-shop` (gitignored).

Output:
```
============================================
  Shop angelegt:
============================================
  Domain:         ki-berater-test.local
  Plan:           starter
  ...
  API-Key:        abc123...
  Webhook-Secret: deadbeef...
============================================
```

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

## Tests laufen lassen

```bash
.venv/Scripts/pytest.exe -v        # alle 182 Tests
.venv/Scripts/ruff.exe check backend
.venv/Scripts/mypy.exe backend
```

---

## Logs anschauen

```bash
# Backend (in dem Terminal wo uvicorn laeuft, kommen die strukturierten Logs)
# Oder Backend-Logs in Datei + tail:
.venv/Scripts/uvicorn.exe backend.main:app --reload > backend.log 2>&1 &
tail -f backend.log

# Docker-Services
docker compose logs -f postgres
docker compose logs -f redis
docker compose logs -f qdrant
```

---

## Postgres direkt anschauen

```bash
docker compose exec postgres psql -U ki -d ki

# Beispiel-Queries:
SELECT count(*) FROM products;
SELECT id, domain, plan FROM shops;
SELECT shop_id, model, sum(cost_eur) FROM llm_usage GROUP BY 1,2;
SELECT * FROM product_clicks ORDER BY clicked_at DESC LIMIT 10;
```

---

## Haeufige Stolpersteine

**`docker compose up` schlaegt fehl: "Cannot connect to the Docker daemon"**
→ Docker Desktop ist nicht gestartet. Tray-Icon checken.

**`alembic upgrade head` schlaegt fehl: "could not connect to server"**
→ Postgres-Container ist noch nicht ready. `docker compose ps` —
warten bis Postgres "healthy" zeigt, dann nochmal.

**Backend startet, aber `/ready` zeigt Postgres als "fail"**
→ `DATABASE_URL` in `.env` falsch. Default ist
`postgresql+asyncpg://ki:ki@localhost:5432/ki` — sollte mit dem
docker-compose.yml uebereinstimmen.

**Plugin-Verbindungstest in WP "Auth fehlgeschlagen"**
→ API-Key falsch eingegeben. Vergleichen mit `.local-shop`.

**Plugin-Verbindungstest "CORS-Error"**
→ Shop-Domain im POST `/v1/shops`-Call passt nicht zur Local-Site-Domain.
Direkt-Update:
```bash
docker compose exec postgres psql -U ki -d ki \
  -c "UPDATE shops SET domain='<korrekte-domain>.local' WHERE id='<shop-id>'"
```
Dann 60 s warten (CORS-Cache).

**Chat antwortet nicht**
→ Backend-Logs checken. Ohne `GOOGLE_API_KEY`/`ANTHROPIC_API_KEY` in
`.env` faellt der Backend auf den Mock-Provider zurueck — du siehst
dann eine immer-gleiche Beispielantwort. Fuer echte Antworten: API-Key
besorgen.

---

## Was nach dem lokalen Test kommt

Siehe [DEPLOY.md](DEPLOY.md) fuer Hetzner-Cloud-Deployment der
Production-Variante, [BILLING_SETUP.md](BILLING_SETUP.md) fuer
Stripe-Konfiguration, [PLUGIN_DISTRIBUTION.md](PLUGIN_DISTRIBUTION.md)
fuer GitHub-Releases als Update-Server.
