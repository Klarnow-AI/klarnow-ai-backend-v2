# Klarnow AI

Agency replacement operating system for non-marketers. Generates and manages a complete campaign delivery pack end-to-end: Brand Strategy (Brand OS), Marketing Plan, Brand Identity, Conversion Page, Campaign Assets, Execution Tracking, Proposals and Invoices, and an exportable Launch Bundle.

## Vision

Enable small businesses to launch and execute professional marketing campaigns without hiring an agency, by combining AI-driven strategy with disciplined execution and revenue workflows.

## Run locally

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- PostgreSQL

### Setup

1. Clone the repo and enter the project directory.
2. Copy env and set values:
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL, SECRET_KEY, etc.
   ```
3. Create venv and install dependencies:
   ```bash
   make install
   # or: uv sync
   ```
4. Run migrations (you run these; see [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md)):
   ```bash
   alembic upgrade head
   ```
5. Start the API:
   ```bash
   make start
   # or: source .env && uvicorn app.main:app --reload
   ```

API: `http://localhost:8000`. Docs: `http://localhost:8000/docs`. Health: `http://localhost:8000/health`.

### Make targets

| Target          | Description                      |
| --------------- | -------------------------------- |
| `make install`  | Create venv and sync deps        |
| `make start`    | Run API with reload (loads .env) |
| `make serve`    | Run API production-style         |
| `make activate` | Print command to activate venv   |

## Environment variables

See [.env.example](.env.example). Required: `DATABASE_URL`, `SECRET_KEY`. Optional: Resend, S3, OpenAI for later phases.

## Documentation

- [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) – Implementation instructions (e.g. who runs migrations).
- [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md) – Phase checklists.
- Product and agentic architecture are defined in the PRD and A-PRD (referenced in the build plan).
