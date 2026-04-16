# LogSentinel Makefile — one-command bring-up + common dev tasks.
#
# Quickstart from a fresh clone:
#   make demo        # docker up, migrate, seed, print dashboard URL
#
# Individual targets:
#   make up          # start postgres (+ redis) via docker-compose
#   make down        # stop containers
#   make migrate     # alembic upgrade head
#   make seed        # ingest full simulator dataset into DB (~50K events)
#   make api         # run FastAPI locally (foreground)
#   make dashboard   # run Vite dev server for the React dashboard
#   make test        # pytest (unit + integration)
#   make perf        # pytest performance benchmarks (requires seeded DB)
#   make baseline    # manual-vs-automated reduction measurement

PYTHON  ?= $(if $(wildcard log_venv/bin/python),log_venv/bin/python,python3)
PIP     ?= $(if $(wildcard log_venv/bin/pip),log_venv/bin/pip,pip3)
PYTEST  ?= $(if $(wildcard log_venv/bin/pytest),log_venv/bin/pytest,pytest)
ALEMBIC ?= $(if $(wildcard log_venv/bin/alembic),log_venv/bin/alembic,alembic)

PG_HOST ?= localhost
PG_PORT ?= 5432

.PHONY: demo up down wait-postgres migrate seed api dashboard dashboard-build \
        test perf baseline clean-db install help

help:
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

demo: up wait-postgres migrate seed  ## End-to-end bring-up: containers + schema + 50K events seeded
	@echo ""
	@echo "================================================================"
	@echo "  LogSentinel is up."
	@echo ""
	@echo "  Next steps (in separate terminals):"
	@echo "    make api         # http://localhost:8000/docs"
	@echo "    make dashboard   # http://localhost:5173"
	@echo "================================================================"

up:  ## Start postgres + redis containers
	docker-compose up -d postgres redis

down:  ## Stop + remove containers
	docker-compose down

wait-postgres:  ## Block until postgres accepts connections
	@echo "Waiting for postgres on $(PG_HOST):$(PG_PORT)..."
	@for i in $$(seq 1 30); do \
		if docker-compose exec -T postgres pg_isready -U logsentinel >/dev/null 2>&1; then \
			echo "  postgres ready"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "  postgres did not become ready in 30s" >&2; exit 1

migrate:  ## Run alembic migrations
	$(ALEMBIC) upgrade head

seed:  ## Bulk-ingest the simulator dataset into postgres
	$(PYTHON) scripts/bulk_ingest.py

api:  ## Run FastAPI locally (foreground, auto-reload)
	$(PYTHON) -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dashboard:  ## Run Vite dev server
	cd dashboard && npm run dev

dashboard-build:  ## Production build of the dashboard
	cd dashboard && npm run build

install:  ## Install Python + dashboard dependencies
	$(PIP) install -r requirements.txt
	cd dashboard && npm install

test:  ## Run pytest (excluding performance benchmarks)
	$(PYTEST) tests/ -v -m "not performance"

perf:  ## Run performance benchmarks (requires seeded DB)
	$(PYTEST) tests/test_performance.py -v -m performance -s

baseline:  ## Measure manual-vs-automated tactic detection (updates benchmark log)
	$(PYTHON) scripts/manual_baseline.py

clean-db:  ## Drop and recreate the logsentinel database (destructive)
	docker-compose exec -T postgres psql -U logsentinel -d postgres \
		-c "DROP DATABASE IF EXISTS logsentinel;" \
		-c "CREATE DATABASE logsentinel OWNER logsentinel;"
