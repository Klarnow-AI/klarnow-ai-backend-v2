ENSURE YOU DO NOT ALWAYS CHANGE USER INTERFACE EXCEPT EXPILICTLY TOLD TO DO SO.
WHEN CHANGING LOGIC OR ADDING FEATURE ENSURE IT DOES AFFECT THE UI EXCEPT I EXPLICITLY TELL YOU TO.
DEVELOP NEW UI USING CONCEPT ON EXISTING UI.
DO NOT MAKE MIGRATONS. I WILL DO IT MYSELF.

# Coding Agent Instructions (Backend + Frontend)

Follow this document when making changes to the backend (`app/`, Python/FastAPI) or the frontend (`frontend/`, Next.js/React). Use clear "Do / Don't" and "When X, do Y" rules.

---

## 1. Cross-cutting (both stacks)

### Repo layout

- Backend code lives under **`app/`**.
- Frontend code lives under **`frontend/`**.
- Do **not** add backend logic under `frontend/` or frontend UI under `app/`.

### API contract

- Backend **defines** the API: routes + Pydantic schemas.
- Frontend **consumes** it via `api_requests/` and `types/api-types`.
- When adding or changing an endpoint:
  1. Update backend route and schema first.
  2. Then update frontend `api_requests` and `types/api-types` (or types under `types/`) so they stay in sync.

### Naming

- Use **consistent domain names** across both (e.g. `chat`, `packs`, `landing`).
- Prefer **snake_case** in Python and in API request/response payloads.
- Use **camelCase** only where the frontend already uses it for existing fields.

### Do not

- Commit secrets or env-specific values.
- Add new global state or new frameworks without alignment with the existing architecture.

---

## 2. Backend (FastAPI / `app/`)

### Entrypoint

- **`app/main.py`** – Mounts routers, CORS, exception handler.
- New domains: add a router here with a clear **prefix** and **tag** (e.g. `prefix="/api/v1/chat"`, `tags=["chat"]`).

### Modules

- One domain per folder under **`app/modules/<domain>/`** (e.g. `chat`, `packs`, `landing`).
- Each module typically has:
  - **`routes.py`** – HTTP handlers only. Parse query/body, call services, return Pydantic models. **No business logic in routes.**
  - **`services.py`** – Business logic and DB access. Receives `Session` and domain ids; returns domain models or raises.
  - **`schemas.py`** – Pydantic request/response models. Use these in routes; keep response shape aligned with frontend `types/api-types` where the frontend calls this API.
  - **`models.py`** – SQLAlchemy models if the domain has DB tables.
  - **Optional:** `tools.py`, `orchestrator_*.py` when the domain has agents/tools.

### Core

- Shared code in **`app/core/`** – auth (deps, JWT, routes), config, errors, db session.
- In routes: use **`get_current_user`** and **`get_db`** from core.
- Do **not** put business logic in `core/`.

### Dependency direction

- **Routes** depend on services and schemas.
- **Services** depend on models and core/db.
- **Schemas** and **models** do not import routes.
- Do **not** import frontend code from backend.

### New endpoint (checklist)

1. Add or update schema(s) in the module’s **`schemas.py`**.
2. Add or update service function(s) in **`services.py`**.
3. Add or update route(s) in **`routes.py`**.
4. If it’s a new module, register the router in **`main.py`**.

---

## 3. Frontend (Next.js / `frontend/`)

### API layer

- All HTTP calls go through **`api_requests/`** by domain (e.g. `api_requests/chat.ts`, `api_requests/packs.ts`).
- Use the shared **`api()`** (or equivalent) from **`lib/http.ts`**; do **not** call `fetch` directly from pages or components.
- Request/response types live in **`types/api-types.ts`** (or a dedicated file under `types/`).
- When the backend adds or changes an endpoint: add or update the corresponding `api_requests` function and types.

### Features and pages

- Route-level UI lives under **`app/`** (e.g. `app/(dashboard)/chat/page.tsx`).
- For a given feature (e.g. chat, packs), use:
  - **`_components/`** – Feature-specific UI (e.g. `ChatMessageList`, `PackCard`). One responsibility per component; prefer files under ~150–200 lines.
  - **`_store/`** (optional) – Zustand store when the feature has shared state used by multiple components.
  - **`helpers.ts`** – Pure helpers and URL/builders for that feature. No JSX.

### Shared UI

- Reusable primitives (buttons, inputs, modals, layout) live in **`components/`** (or `components/ui/`).
- Do **not** put feature-specific screens or heavy business logic there.

### State

- **Transient UI state** (e.g. modal open, tab index) → component state.
- **Shared feature state** → the feature’s `_store` or existing context (e.g. auth).
- Do **not** add new global stores or context without aligning with the existing pattern.

### Hooks

- Data-fetching hooks live in **`hooks/`**.
- Use **`api_requests`** and **`types`** inside hooks.
- Prefer **`useGet`** / **`usePost`** when adding new fetch logic.

### Dependency direction

- **Pages and components** import from `hooks`, `api_requests`, `types`, `components`, `lib`.
- **`api_requests`** and **`types`** do **not** import from pages or components.

---

## 4. File size and componentization (frontend)

- If a single file exceeds **~150–200 lines**, look for a named section (e.g. Header, Footer, a repeated list item) and extract it into a component under the feature’s **`_components/`** or **`components/`** if it’s shared.
- Name components by **concept** (e.g. `LandingHeader`, `ChatMessageItem`).
- **Type all props**; avoid `any`.

---

## 5. What the agent must not do (both)

- Do **not** add secrets or hardcoded credentials.
- Do **not** break the dependency rules above (e.g. no `api_requests` importing UI; no routes containing business logic).
- Do **not** introduce a new backend or frontend framework or a new global state library without explicit approval.
- Do **not** change API response shapes (or frontend types) without updating the other side so they stay in sync.
