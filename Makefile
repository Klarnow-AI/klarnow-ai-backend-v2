SHELL := /bin/bash
VENV := $(abspath .venv)
PYTHON := $(VENV)/bin/python
UVICORN := $(PYTHON) -m uvicorn
ALEMBIC := $(PYTHON) -m alembic
PIP := $(VENV)/bin/pip

# Migration message (can be overridden: make migrate message="your message")
message ?= auto migration

.PHONY: create install update run activate clean start worker serve migrate upgrade-migration build-frontend build brand-os onboarding-flow onboarding-demo

create:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv "$(VENV)"; \
	fi

install: create
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

update: create
	$(PIP) install --upgrade pip
	$(PIP) install -U -r requirements.txt

run: start

start: create
	$(UVICORN) app.main:app --reload

worker: create
	$(PYTHON) -m app.workers.onboarding_worker

brand-os: create
	@if [ -z "$(pack_id)" ]; then \
		echo "Usage: make brand-os pack_id=<uuid> [args='--show-full']"; \
		exit 1; \
	fi
	$(PYTHON) scripts/run_brand_os.py $(pack_id) $(args)

onboarding-flow: create
	@if [ -z "$(pack_id)" ]; then \
		echo "Usage: make onboarding-flow pack_id=<uuid> [args='--show-artifacts']"; \
		exit 1; \
	fi
	$(PYTHON) scripts/run_onboarding_flow.py $(pack_id) $(args)

onboarding-demo: create
	$(PYTHON) scripts/run_onboarding_demo.py $(args)

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
