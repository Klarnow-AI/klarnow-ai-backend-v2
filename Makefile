SHELL := /bin/bash
VENV := $(abspath .venv)
UVICORN := $(VENV)/bin/uvicorn
PYTHON := $(VENV)/bin/python
UV := uv
ALEMBIC := $(VENV)/bin/alembic
export UV_PROJECT_ENVIRONMENT := $(VENV)

# Migration message (can be overridden: make migrate message="your message")
message ?= auto migration

.PHONY: init create install update sync run activate clean import start worker serve migrate upgrade-migration build-frontend build

init:
	$(UV) init

create:
	@if [ ! -d "$(VENV)" ]; then \
		$(UV) venv "$(VENV)"; \
	fi

sync: create
	$(UV) sync

import:
	$(UV) add -r requirements.txt
	$(UV) sync

install: create
	@if [ -f pyproject.toml ]; then \
		$(UV) sync; \
	elif [ -f requirements.txt ]; then \
		$(UV) pip install --python "$(PYTHON)" -r requirements.txt; \
	else \
		echo "No pyproject.toml or requirements.txt found."; \
		exit 1; \
	fi

update: create
	@if [ -f pyproject.toml ]; then \
		$(UV) sync; \
	elif [ -f requirements.txt ]; then \
		$(UV) pip install --python "$(PYTHON)" -U -r requirements.txt; \
	else \
		echo "No pyproject.toml or requirements.txt found."; \
		exit 1; \
	fi

run: start

start: create
	$(UVICORN) app.main:app --reload

worker: create
	$(PYTHON) -m app.workers.onboarding_worker

serve: create
	port=$${PORT:-8000}; $(UVICORN) app.main:app --host 0.0.0.0 --port $$port

activate:
	@echo "Run: source $(VENV)/bin/activate"

clean:
	rm -rf $(VENV)

migrate: create
	$(ALEMBIC) revision --autogenerate -m "$(message)"

upgrade-migration: create
	$(ALEMBIC) upgrade head

build-frontend:
	cd frontend && bun install && bun run build

build: install build-frontend
	@echo "Backend and frontend built. Run 'make serve' to start production server."
