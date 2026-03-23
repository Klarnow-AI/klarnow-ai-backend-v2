SHELL := /bin/bash
BACKEND_DIR := backend
BACKEND_TARGETS := init create sync import install update run start worker serve activate clean migrate upgrade-migration

.PHONY: $(BACKEND_TARGETS) build-frontend build

$(BACKEND_TARGETS):
	$(MAKE) -C $(BACKEND_DIR) $@

build-frontend:
	cd frontend && bun install && bun run build

build: install build-frontend
	@echo "Backend and frontend built. Run 'make serve' to start production server."
