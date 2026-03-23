# Klarnow Backend

This directory contains the Python backend for Klarnow AI: the FastAPI app, Alembic migrations, helper scripts, tests, and Supabase config.

Common commands:

- `uv sync`
- `alembic upgrade head`
- `uvicorn app.main:app --reload`
- `python -m pytest -q`

Environment variables are loaded from the repository root `.env`. Use [`backend/.env.example`](./.env.example) as the template when creating or updating that file.
