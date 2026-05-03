# KI-Verkaufsberater für WooCommerce

SaaS-Plugin: KI-Chatbot in WooCommerce-Shops. Endkunden stellen
Beratungsfragen, die KI berät auf Basis des Produktkatalogs und empfiehlt
Artikel. DSGVO-konform aus Frankfurt, Streaming-Antworten, Conversion-
Tracking inkludiert.

**Status:** Code ~95% fertig (182 Tests grün), GitHub-Repo live, erstes
Plugin-Release `plugin-v0.1.0` getaggt. Production-Deploy + Pilot-Akquise
stehen aus.

---

## Repo-Layout (Monorepo)

```
ki-berater/
├── backend/                 # FastAPI Backend (Python 3.12)
│   ├── api/v1/              # HTTP-Endpoints
│   ├── billing/             # Stripe + Plan-Limits
│   ├── core/                # Config, Logging, Security, Sentry
│   ├── db/                  # Session, tenant_query
│   ├── embeddings/          # Gemini text-embedding-004
│   ├── llm/                 # Provider-Router, Cost-Tracking, Streaming
│   ├── models/              # SQLAlchemy 2.0
│   ├── prompts/             # System-Prompt-Builder
│   ├── schemas/             # Pydantic v2
│   ├── services/            # Business-Logik
│   ├── vectordb/            # Qdrant-Wrapper
│   ├── alembic/versions/    # 6 Migrations
│   └── tests/               # 182 pytest tests
├── plugin/ki-berater/       # WordPress-Plugin (PHP 8, GPL-2.0)
│   ├── includes/            # Settings, Widget, Sync, Conversion-Tracker
│   └── assets/              # Vanilla JS Widget (~16 KB)
├── landing/                 # Astro 5 + Tailwind 4 Landing-Page
├── scripts/                 # backup-postgres.sh, create-test-shop.sh
├── .github/workflows/       # CI (backend + plugin) + Release-on-Tag
├── Dockerfile               # Multi-stage Backend-Image
├── docker-compose.yml       # Dev: postgres + redis + qdrant
├── docker-compose.prod.yml  # Prod: + backend + caddy
└── Caddyfile                # Reverse-Proxy mit auto-HTTPS
```

---

## Quick-Start

Detaillierte Anleitung: **[LOCAL_SETUP.md](LOCAL_SETUP.md)** — kein Docker nötig.

```text
1. Doppelklick start-dev.bat        → Backend (embedded Postgres) läuft
2. bash scripts/create-test-shop.sh → API-Key + Webhook-Secret in .local-shop
3. Local von Flywheel: Site provisionieren
4. Doppelklick link-plugin-to-wp.bat → Site-Name → Junction
5. WP-Admin → Plugin aktivieren → Settings füllen → "Verbindung testen"
6. Frontend → Chat-Bubble → fragen → KI antwortet
```

Ohne `GOOGLE_API_KEY` läuft das Backend in Dev mit einem Mock-Provider —
Chat-Flow funktioniert end-to-end, Antworten sind aber statisch.

---

## Architektur-Entscheidungen

| Bereich | Entscheidung |
|---|---|
| Multi-Tenancy | Application-Level `shop_id`-Filter via SQLAlchemy-Mixin + zentraler `tenant_select()`-Wrapper |
| Vector-DB | Eine globale Qdrant-Collection `products`, `shop_id` als indiziertes Payload-Field |
| LLM-Routing | Heuristik-first (Token-Count + Keywords), Provider-Fallback-Chain |
| Streaming | SSE über `/v1/conversations/stream` und `/messages/stream` |
| Produkt-Sync | WooCommerce-Webhook → Sofort-Reindex (HMAC-signiert) |
| Pricing | Pure Subscription mit Hard-Cap (300/1500/5000/Custom) |
| Conversion-Attribution | Cookie-basiert + Strict-Match `products_referenced ∩ order.items` |
| Plugin-Distribution | GitHub-Releases via PUC v5 (Plugin Update Checker) |

---

## Sanity-Checks

```bash
.venv/Scripts/ruff.exe check backend       # lint
.venv/Scripts/mypy.exe backend             # strict typing
.venv/Scripts/pytest.exe                   # 182 tests
```

---

## Dokumentation

| Datei | Inhalt |
|---|---|
| [LOCAL_SETUP.md](LOCAL_SETUP.md) | Lokales Dev-Setup, Quick-Start, Troubleshooting |
| [DEPLOY.md](DEPLOY.md) | Hetzner-Cloud-Deployment (CX22 + Caddy + auto-HTTPS) |
| [BILLING_SETUP.md](BILLING_SETUP.md) | Stripe-Account + Products + Webhook-Endpoint |
| [PLUGIN_DISTRIBUTION.md](PLUGIN_DISTRIBUTION.md) | GitHub-Releases als Update-Server für WP-Plugin |
| [SECURITY.md](SECURITY.md) | Threat-Model, Controls, Responsible Disclosure |

---

## Endpoints (Auswahl)

| Method | Pfad | Auth |
|---|---|---|
| `POST` | `/v1/shops` | X-Admin-Key |
| `GET` | `/v1/shops/me` | X-Api-Key |
| `GET` | `/v1/shops/me/export` | X-Api-Key (DSGVO Art. 15) |
| `POST` | `/v1/conversations` | X-Api-Key |
| `POST` | `/v1/conversations/stream` | X-Api-Key (SSE) |
| `POST` | `/v1/conversations/{id}/messages/stream` | X-Api-Key (SSE) |
| `POST` | `/v1/conversations/{id}/clicks` | X-Api-Key |
| `POST` | `/v1/conversations/{id}/conversion` | X-Api-Key |
| `POST` | `/v1/products` | X-Api-Key |
| `POST` | `/v1/products/sync` | X-Api-Key (async) |
| `POST` | `/v1/webhooks/products` | HMAC + X-Api-Key |
| `POST` | `/v1/webhooks/stripe` | Stripe-Signature |
| `POST` | `/v1/billing/checkout` | X-Api-Key |
| `POST` | `/v1/billing/portal` | X-Api-Key |
| `GET` | `/v1/billing/quota` | X-Api-Key |
| `GET` | `/v1/analytics/overview` | X-Api-Key |
| `GET` | `/health` | none |
| `GET` | `/ready` | none (deep healthcheck) |

---

## Lizenzen

- Backend, Landing, Skripte: TBD (privat / proprietär)
- WordPress-Plugin: **GPL-2.0-or-later** (WordPress-Pflicht)
