# Atajos comunes. Funciona en bash/WSL; en PowerShell usar los comandos directos.

COMPOSE = docker compose

.PHONY: help up down logs seed migrate test test-python test-frontend lint scale-text scale-image clean

help:
	@echo "Comandos disponibles:"
	@echo "  make up            - Levantar todo el stack"
	@echo "  make down          - Apagar (preservando volumenes)"
	@echo "  make clean         - Apagar y borrar volumenes"
	@echo "  make logs          - Tail de logs del stack"
	@echo "  make seed          - Crear admin/analyst demo"
	@echo "  make migrate       - Aplicar migraciones Alembic"
	@echo "  make test          - Correr todos los tests"
	@echo "  make scale-text N=4    - Escalar worker_text a N replicas"
	@echo "  make scale-image N=3   - Escalar worker_image a N replicas"

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=100

seed:
	$(COMPOSE) exec api python -m services.api.app.infrastructure.seed

migrate:
	$(COMPOSE) exec api alembic -c /app/services/shared/alembic.ini upgrade head

test: test-python test-frontend

test-python:
	$(COMPOSE) run --rm api pytest services/api/tests
	$(COMPOSE) run --rm worker_text pytest services/worker_text/tests
	$(COMPOSE) run --rm worker_image pytest services/worker_image/tests
	$(COMPOSE) run --rm worker_aggregator pytest services/worker_aggregator/tests
	$(COMPOSE) run --rm worker_audio pytest services/worker_audio/tests

test-frontend:
	cd dashboard && npm test

scale-text:
	$(COMPOSE) up -d --scale worker_text=$(N)

scale-image:
	$(COMPOSE) up -d --scale worker_image=$(N)

lint:
	$(COMPOSE) run --rm api ruff check services
