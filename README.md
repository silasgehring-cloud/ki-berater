# KI-Verkaufsberater für WooCommerce

SaaS-Plugin: KI-Chatbot in WooCommerce-Shops. Endkunden stellen Beratungsfragen, die KI berät auf Basis des Produktkatalogs und empfiehlt Artikel.

## Quick start

```bash
# 1. Python-Deps installieren (editable + dev tools)
make install

# 2. Services starten (Postgres, Redis, Qdrant)
make up

# 3. .env anlegen
cp .env.example .env

# 4. DB-Schema migrieren
make migrate

# 5. Backend starten
make dev
# → http://localhost:8000/health
```

## Sanity-Checks

```bash
make lint     # ruff check + mypy strict
make test     # pytest (mit asyncio_mode=auto)
make format   # ruff format + import-Sortierung
```

## Projekt-Layout

```
ki-berater/
├── backend/             # FastAPI Backend (Python 3.12)
│   ├── api/             # HTTP-Endpoints (v1)
│   ├── core/            # Config, Logging, Security
│   ├── llm/             # Provider-Router, Cost-Tracking
│   ├── embeddings/      # Gemini text-embedding-004
│   ├── vectordb/        # Qdrant-Wrapper
│   ├── services/        # Business-Logik
│   ├── models/          # SQLAlchemy 2.0
│   ├── schemas/         # Pydantic (Request/Response)
│   ├── alembic/         # DB-Migrations
│   └── tests/           # pytest
├── plugin/ki-berater/   # WordPress-Plugin (Phase 2)
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Architektur (Foundation-Entscheidungen)

| Bereich | Entscheidung |
|---|---|
| Multi-Tenancy | Application-Level `shop_id`-Filter via SQLAlchemy-Mixin |
| Vector-DB | Eine globale Qdrant-Collection, `shop_id` als Payload-Filter |
| LLM-Routing | Heuristik-first (Token-Count + Keywords), Klassifikator später |
| Streaming | Phase 1: keines (POST→Response). Streaming in Phase 2/3 |
| Produkt-Sync | WooCommerce-Webhook → Sofort-Reindex |

Vollständiger Plan: `~/.claude/plans/ki-verkaufsberater-f-r-woocommerce-precious-sedgewick.md`

## Status

Sprint 0 (Setup) — in Arbeit. Folgt: Sprint 1.1 (Datenmodell + API-Skeleton), Sprint 1.2 (LLM-Layer).
