.PHONY: help install dev test test-unit lint format migrate migration up down logs \
        prod-deploy prod-up prod-down prod-logs prod-ps prod-backup prod-shell prod-migrate \
        plugin-zip plugin-clean

help:
	@echo "Local dev:"
	@echo "  make install         - Install Python deps (editable + dev)"
	@echo "  make dev             - Run FastAPI with auto-reload"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only (no integration markers)"
	@echo "  make lint            - Run ruff + mypy"
	@echo "  make format          - Format code (ruff format + import sort)"
	@echo "  make migrate         - Apply DB migrations"
	@echo "  make migration name=NAME - Create new auto-generated migration"
	@echo "  make up              - Start docker services (postgres, redis, qdrant)"
	@echo "  make down            - Stop docker services"
	@echo "  make logs            - Tail service logs"
	@echo ""
	@echo "Production (on server):"
	@echo "  make prod-deploy     - Build + start prod stack"
	@echo "  make prod-up         - Start prod stack (no rebuild)"
	@echo "  make prod-down       - Stop prod stack"
	@echo "  make prod-logs       - Tail prod logs"
	@echo "  make prod-ps         - List prod containers"
	@echo "  make prod-backup     - Run pg_dump now"
	@echo "  make prod-shell      - Shell into backend container"
	@echo "  make prod-migrate    - Run alembic upgrade head in prod"

install:
	pip install -e ".[dev]"

dev:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

test-unit:
	pytest -m "not integration"

lint:
	ruff check backend
	mypy backend

format:
	ruff format backend
	ruff check --fix --select I backend

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(name)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# ----- Production targets (run on the server) -----

prod-deploy:
	docker compose -f docker-compose.prod.yml up -d --build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=200

prod-ps:
	docker compose -f docker-compose.prod.yml ps

prod-backup:
	docker compose -f docker-compose.prod.yml exec postgres sh /usr/local/bin/backup-postgres.sh

prod-shell:
	docker compose -f docker-compose.prod.yml exec backend /bin/bash

prod-migrate:
	docker compose -f docker-compose.prod.yml exec backend alembic -c backend/alembic.ini upgrade head

# ----- Plugin distribution -----

plugin-clean:
	rm -rf plugin/ki-berater/vendor dist/

# Build a WP-installable zip (with vendor/, without dev files).
# Used locally when you want to test an update before tagging.
plugin-zip:
	cd plugin/ki-berater && composer install --no-dev --no-interaction --optimize-autoloader
	mkdir -p dist staging
	rsync -av \
		--exclude='.git' \
		--exclude='.gitignore' \
		--exclude='composer.json' \
		--exclude='composer.lock' \
		--exclude='phpstan.neon' \
		--exclude='phpunit.xml*' \
		--exclude='tests/' \
		--exclude='.distignore' \
		plugin/ki-berater/ staging/ki-berater/
	cd staging && zip -r ../dist/ki-berater.zip ki-berater
	rm -rf staging
	@echo "Built: dist/ki-berater.zip"
