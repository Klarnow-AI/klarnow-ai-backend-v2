SHELL := /bin/bash
VENV := .venv
UVICORN := $(VENV)/bin/uvicorn
PYTHON := $(VENV)/bin/python
UV := uv
ALEMBIC := $(VENV)/bin/alembic

# Migration message (can be overridden: make migrate MESSAGE="your message")
message ?= "auto migration"

.PHONY: init create install update sync run activate clean import start worker build-frontend build serve

init:
	$(UV) init

create:
	@if [ ! -d "$(VENV)" ]; then \
		$(UV) venv $(VENV); \
	fi

sync: create
	$(UV) sync

import:
	uv add -r requirements.txt
	uv sync


install: create
	@if [ -f pyproject.toml ]; then \
		$(UV) sync; \
	elif [ -f requirements.txt ]; then \
		$(UV) pip install -r requirements.txt; \
	else \
		echo "No pyproject.toml or requirements.txt found."; \
		exit 1; \
	fi

update: create
	@if [ -f pyproject.toml ]; then \
		$(UV) sync; \
	elif [ -f requirements.txt ]; then \
		$(UV) pip install -U -r requirements.txt; \
	else \
		echo "No pyproject.toml or requirements.txt found."; \
		exit 1; \
	fi

run: create
	$(PYTHON) main.py

start:
	set -a && [ -f .env ] && . .env; set +a && $(UVICORN) app.main:app --reload

worker:
	set -a && [ -f .env ] && . .env; set +a && $(PYTHON) -m app.workers.onboarding_worker

build-frontend:
	cd frontend && npm install && npm run build

build: install build-frontend
	@echo "Backend and frontend built. Run 'make serve' to start production server."

serve:
	set -a && [ -f .env ] && . .env; set +a && PORT=$${PORT:-8000} $(UVICORN) app.main:app --host 0.0.0.0 --port $$PORT

activate:
	@echo "Run: source $(VENV)/bin/activate"

clean:
	rm -rf $(VENV)

migrate:
	$(ALEMBIC) revision --autogenerate -m "$(message)"

upgrade-migration:
	$(ALEMBIC) upgrade head
