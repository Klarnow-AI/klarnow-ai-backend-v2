# Klarnow AI

Agency replacement operating system for non-marketers. Generates and manages a complete campaign delivery pack end-to-end: Brand Strategy (Brand OS), Marketing Plan, Brand Identity, Conversion Page, Campaign Assets, Execution Tracking, Proposals and Invoices, and an exportable Launch Bundle.

## Vision

Enable small businesses to launch and execute professional marketing campaigns without hiring an agency, by combining AI-driven strategy with disciplined execution and revenue workflows.

## Run locally

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- PostgreSQL
- Redis

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
6. Start the onboarding worker in a separate terminal:
   ```bash
   make worker
   # or: source .env && python -m app.workers.onboarding_worker
   ```

API: `http://localhost:8000`. Docs: `http://localhost:8000/docs`. Health: `http://localhost:8000/health`.

### Make targets

| Target          | Description                      |
| --------------- | -------------------------------- |
| `make install`  | Create venv and sync deps        |
| `make start`    | Run API with reload (loads .env) |
| `make worker`   | Run Redis onboarding worker      |
| `make serve`    | Run API production-style         |
| `make activate` | Print command to activate venv   |

## Environment variables

See [.env.example](.env.example). Required: `DATABASE_URL`, `SECRET_KEY`, and `REDIS_URL` for background onboarding. Optional: Resend, S3, OpenAI, and Google sign-in.
`CORS_ALLOW_ORIGINS` accepts a JSON list (recommended), comma-separated values, and bracketed forms that are normalized.

### Staging/production API + CORS checklist

1. Backend: set `CORS_ALLOW_ORIGINS` to include your frontend origin, e.g. `["https://staging.klarnow.ai"]`.
2. Backend: set `GOOGLE_OAUTH_CLIENT_ID` to your web OAuth client ID.
3. Frontend: set `NEXT_PUBLIC_API_URL` to your hosted backend URL (never localhost).
4. Frontend: set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to the same OAuth client ID.
5. Rebuild and redeploy frontend after any `NEXT_PUBLIC_*` env change.

Staging Docker build/run example:

```bash
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://api.staging.klarnow.ai \
  --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=<staging-google-client-id> \
  -t klarnow-frontend:staging .

docker run --rm -p 3000:3000 \
  -e BACKEND_URL=https://api.staging.klarnow.ai \
  klarnow-frontend:staging
```

GitHub Actions CI (`.github/workflows/frontend-build.yml`) builds with:
- `NEXT_PUBLIC_API_URL=https://api.staging.klarnow.ai`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` from repository/environment variable `STAGING_NEXT_PUBLIC_GOOGLE_CLIENT_ID`

Staging backend env example:

```bash
CORS_ALLOW_ORIGINS='["https://staging.klarnow.ai"]'
```

### Google Sign-In setup (GIS ID token flow)

1. Create a Google OAuth client ID for a Web application.
2. Add frontend origins (local/staging/production) in Google Cloud Console:
   - `http://localhost:3000`
   - your staging frontend origin
   - your production frontend origin
3. Set `GOOGLE_OAUTH_CLIENT_ID` in backend `.env`.
4. Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in `frontend/.env.local` (and deployment envs).

After Google token verification, backend still returns the app JWT used by existing protected routes.

### Published website builder sites (subdomain URLs)

To serve published sites at brand-name subdomains (e.g. `acme.klarnow.ai`) instead of path-based URLs:

- **Staging:** Set `SITES_DOMAIN=staging.klarnow.ai` in the staging environment. Published URLs will be `{brand-slug}.staging.klarnow.ai`.
- **Production:** Set `SITES_DOMAIN=klarnow.ai` (or `sites.klarnow.ai`) for URLs like `{brand-slug}.klarnow.ai`.

**Infrastructure:** Configure wildcard DNS (A or CNAME record) for `*.staging.klarnow.ai` and `*.klarnow.ai` pointing to the same backend. Ensure the load balancer or reverse proxy forwards the `Host` header so the subdomain router can resolve the correct site.

## Documentation

- [docs/INSTRUCTIONS.md](docs/INSTRUCTIONS.md) – Implementation instructions (e.g. who runs migrations).
- [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md) – Phase checklists.
- Product and agentic architecture are defined in the PRD and A-PRD (referenced in the build plan).
