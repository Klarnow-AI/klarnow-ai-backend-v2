# Klarnow AI – Acceptance Criteria by Phase

Checklists for each phase. Mark items as complete when the criterion is met.

---

## Phase 0: Foundation (weeks 1–2)

**Goal**: Repo cleanup, app skeleton, DB, auth, and config so all later work has a single place to land.

### Repo and docs

- [ ] README.md describes Klarnow AI (product overview, vision), not the prior API Docs Agent project.
- [ ] README includes: how to run locally (uv, Makefile), required env vars, and link/reference to PRD and A-PRD.
- [ ] Makefile typo fixed: `wSHELL` → `SHELL`.
- [ ] Makefile `start`/`serve` load `.env` when present (or doc states to source .env manually).
- [ ] `.env.example` exists with all required variable names and placeholder/empty values (no secrets).
- [ ] `.gitignore` excludes `.env` and `.venv`.

### Backend structure

- [ ] FastAPI app bootstrapped in `app/main.py` with CORS using `FRONTEND_URL`.
- [ ] Health check endpoint exists (e.g. `GET /health` or `GET /api/health`) and returns 200.
- [ ] Top-level folders exist: `app/core/`, `app/modules/`, `app/shared/`.
- [ ] `app/core/` contains: `config.py`, `db/`, `auth/`, `governance.py`, `errors.py` (stubs ok).
- [ ] `app/core/config.py` uses Pydantic Settings for: `DATABASE_URL`, `OPENAI_API_KEY`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRY_TIME`, Resend, S3 (and any other env used). No secrets hardcoded in code.
- [ ] `app/modules/` contains at least one module (e.g. `packs`) with a router that can be mounted.
- [ ] `app/main.py` mounts the module router(s) under a consistent prefix (e.g. `/api/v1/...`).

### Database

- [ ] SQLAlchemy 2.x and Alembic are in use. `app/core/db/session.py` and `app/core/db/base.py` exist.
- [ ] `alembic.ini` and `alembic/env.py` exist and use the app’s DB config/session.
- [ ] First migration creates: `user` table (e.g. id, email, hashed_password, created_at, etc.), and optionally `organisation` if multi-tenant.
- [ ] First migration creates: `pack` table with at least `id`, `name`, `status`, `created_at`, `updated_at`, `created_by_user_id` (FK to user).
- [ ] Migration runs successfully against a local or dev database.

### Auth

- [ ] Login flow exists (e.g. email + password or magic link via Resend) and returns a JWT.
- [ ] JWT is signed with `SECRET_KEY` and respects `ACCESS_TOKEN_EXPIRY_TIME`.
- [ ] A dependency or middleware loads the current user from the JWT and attaches it to the request.
- [ ] At least one route is protected (e.g. “list my packs”): returns 401 without valid token, returns data scoped to the authenticated user with valid token.

### Phase 0 sign-off

- [ ] App starts with `make start` (or equivalent) and serves the health check.
- [ ] Authenticated request to the protected route returns packs (or empty list) for that user only.

---

## Phase 1: Core data model and Pack lifecycle (weeks 3–5)

**Goal**: Domain model for Brand OS, Marketing Plan, Campaign (with Goal object and one CTA), and onboarding; all versioned and referenced by Pack.

### Data model

- [ ] `brand_os` table exists: `pack_id`, `version`, `mission`, `vision`, `values` (JSON), `positioning` (JSON), `personas` (JSON), `voice_and_messaging` (JSON), `is_active`, `created_at`. Active version per pack is identifiable (e.g. `pack.active_brand_os_version` or `pack_state`).
- [ ] `marketing_plan` table exists: `pack_id`, `version`, `plan_type` (30_day | 90_day), `content` (JSON), `is_active`, `created_at`.
- [ ] `campaign` table exists: `pack_id`, `version`, `primary_cta` (single), `goal` (JSONB with metric_type, target_value, time_horizon_days, primary_channel, conversion_action), `angles` (JSON), `active_angle_id` (optional). One CTA enforced (constraint or service layer).
- [ ] Onboarding: either `onboarding_session` table or `pack.onboarding_answers` (JSON). Max 6 questions represented in schema/validation.
- [ ] Migrations for the above run successfully.

### APIs

- [ ] Pack: create (optional start onboarding), list (scoped to user), get by id, archive. Create creates an empty pack and optionally stores onboarding state.
- [ ] Onboarding: submit answers; endpoint to complete onboarding (ready to trigger strategy generation in Phase 2).
- [ ] Brand OS: get active for pack, list versions for pack, get by version. No write endpoints (writes via tools in Phase 2).
- [ ] Marketing Plan: same pattern; filter by `plan_type` where relevant.
- [ ] Campaign: get/set goal, primary CTA, angles, active angle. All campaign writes validate one CTA and call governance for no revenue guarantees where applicable.

### Governance (stub)

- [ ] `app/core/governance.py` exists with at least: `validate_one_cta(campaign)`, `validate_no_revenue_guarantees(text)`, `check_locked_window(plan, window_type)` (stub implementation ok).
- [ ] Campaign update (or relevant API) calls governance; invalid state returns 400 with clear error (no silent bypass).

### Phase 1 sign-off

- [ ] Can create a pack, complete onboarding (answers stored), and read back pack with onboarding state.
- [ ] Can create/update campaign with a single CTA and goal; violating one-CTA or revenue-guarantee rule is rejected.
- [ ] Brand OS and Marketing Plan are read-only via API; versioning fields and active version are in place for Phase 2 tools.

---

## Phase 2: Agentic control plane and tools (weeks 6–9)

**Goal**: Orchestrator as single entry point; tool registry; specialist agents that only act via tools; all state changes through tools.

### Tool system

- [ ] Central tool registry in `app/modules/agents/` (e.g. `registry.py`): each tool has name, description, input/output schema, side effects, allowed agents.
- [ ] At least two domain tools exist and are registered: e.g. `generate_brand_os` (in `app/modules/brand_os/tools.py` or similar), `generate_marketing_plan` (in `app/modules/marketing_plan/tools.py` or similar). Optionally `update_campaign_angles`.
- [ ] Tool execution: input validated against schema; execution logged (tool name, agent, pack_id, sanitised inputs, success/failure, timestamp). No agent code writing directly to DB; only tool code performs writes.
- [ ] Permission matrix: agent → list of tool names. Orchestrator allowed to call any tool; Strategy agent only `generate_brand_os`, etc., as per A-PRD.

### Orchestrator

- [ ] Single orchestrator in `app/modules/agents/orchestrator.py`: accepts user intent (from API or Chat stub), classifies intent, assembles context (pack, active Brand OS, campaign, goal), selects specialist, builds execution plan, runs tools in order with max chain length limit, handles errors and retries (with cap).
- [ ] Orchestrator uses OpenAI (or chosen LLM) function/tool-calling; “functions” are the registered tool names and schemas. No direct DB access in orchestrator logic.

### Specialist agents

- [ ] Strategy Agent: invokes only `generate_brand_os`; input pack_id and onboarding/context; output is a new version (B if A exists). Writes only via tool.
- [ ] Marketing Agent: invokes only `generate_marketing_plan`; input pack_id, plan_type, brand_os context; output new version.

### Goal object and memory

- [ ] Goal object stored in `campaign.goal` (JSONB); injected into orchestrator and specialists when relevant.
- [ ] Decision log: table or append-only store for tool calls (tool, agent, pack_id, sanitised inputs, result, timestamp). Log is written on each tool run.

### Phase 2 sign-off

- [ ] Completing onboarding (via API or test) triggers Orchestrator → Strategy → Marketing tools and produces at least Brand OS and Marketing Plan (new versions).
- [ ] Decision log contains entries for each tool run. No state mutation occurs outside the tool layer.

---

## Phase 3: Conversion page, Plan & Tracker, creative production (weeks 10–14)

**Goal**: Conversion page (draft/publish, live URL, exports), Plan & Tracker with 7/30/90 locks, and creative (posters + Ad Factory video).

### Conversion page

- [ ] `conversion_page` table/model: `pack_id`, `version`, `structure` (JSON), `published_at`, `live_url`, `seo_metadata` (JSON). Draft vs published by version + `published_at` not null.
- [ ] **React-driven structure**: `structure` is JSON that drives React components (sections with type + props); no HTML as primary format.
- [ ] **Live preview**: API returns current draft/version payload (structure + metadata) so frontend can render with React in real time; preview endpoint for editor/view.
- [ ] Tool `generate_conversion_page` (Conversion Agent): input pack_id and context; output new version; CTA in page matches `campaign.primary_cta` (compliance).
- [ ] APIs: get draft/published, **preview** (structure for React), update draft, publish (set live_url, published_at) with governance check (CTA match, no revenue guarantees).
- [ ] Export: React payload (structure + metadata) via API; optional HTML generated from React for Launch Pack.

### Plan and Tracker

- [ ] `plan_tracker` (and related) model: `pack_id`, `horizon` (7 | 30 | 90), `plan_content` (JSON), `unlock_schedule`, `daily_status`, `weekly_checkpoint` (JSON or tables).
- [ ] Lock rules enforced in service layer and `app/core/governance.py`: 7-day editable; 30-day weekly unlock; 90-day staged unlock.
- [ ] APIs: get plan, update 7-day window, submit daily status, weekly checkpoint. Reflection trigger “weekly checkpoint” can be hooked after checkpoint (Phase 7).

### Posters and flyers

- [ ] `asset` table: type (poster | flyer | video), `pack_id`, `version`, `template_id`, `output_key` (S3), `created_at` (and video fields if needed).
- [ ] Tool `render_poster`: template-based, brand applied, output PNG/PDF to S3.

### Ad Factory (video)

- [ ] Video assets in same `asset` model; optional `script`, `srt_key`.
- [ ] Tool `render_video`: batch 1–5, script from angles/brand, safe area enforced, MP4 + SRT to S3.

### Governance

- [ ] Before conversion page publish: CTA match and no revenue guarantees checked; failure returns clear error.
- [ ] Before any asset render: compliance check on copy and CTA.

### Phase 3 sign-off

- [ ] Conversion page can be generated, edited (draft), and published with governance; live preview uses React; export produces React payload (structure + metadata).
- [ ] Plan & Tracker supports 7/30/90 and lock rules; daily status and weekly checkpoint can be submitted.
- [ ] Poster and video tools run successfully and produce assets in S3; governance blocks non-compliant content.

---

## Phase 4: Clients, revenue workflows, Proof Vault, Export (weeks 15–18)

**Goal**: Client management, proposal and invoice lifecycles, reminder automation, proof collection, and Launch Pack export.

### Clients

- [ ] `client` model: e.g. `user_id` or `organisation_id`, name, email, company, etc.
- [ ] APIs: CRUD clients; link client to pack (e.g. `pack.client_id`).

### Proposals and invoices

- [ ] `proposal` and `invoice` models: status lifecycle, amounts, due dates, link to pack and client.
- [ ] Tools `create_proposal`, `create_invoice` (Revenue Agent): create draft only; user approves sending.
- [ ] Reminder: background job or scheduled task for overdue invoices; send via Resend (no automated ad spend).

### Proof Vault

- [ ] `proof` model: `pack_id`, file key (S3), tags, `uploaded_at`.
- [ ] APIs: upload, list, tag, delete.
- [ ] Governance: “required before launch” – before publish or export, either proof exists or user confirms waiver; otherwise block with clear message.

### Export system

- [ ] Launch Pack: ZIP with selected deliverables (Brand OS PDF, Marketing Plan, conversion page HTML/React, assets, proposal, invoice). Structured naming (e.g. `pack_slug_brand_os_vA.pdf`).
- [ ] API “Build Launch Pack”: collect assets, generate PDFs, assemble ZIP, upload to S3, return download link. Optional: selective download per artifact.
- [ ] Before export: full compliance run (CTA, no guarantees, proof if required).

### Phase 4 sign-off

- [ ] Client can be created and linked to a pack; proposal and invoice drafts can be created via tool and approved by user; reminder sends for overdue invoice.
- [ ] Proof can be uploaded and tagged; publish/export is blocked without proof (or waiver) when required.
- [ ] Launch Pack build produces ZIP with correct contents and naming; download link works; compliance blocks export when rules are not met.

---

## Phase 5: Chat with Klaro (weeks 19–21)

**Goal**: Global and pack-scoped chat; Use / Preview / Apply workflow; version-safe regeneration; persistent memory.

### Chat API

- [ ] `conversation` (optional `pack_id`) and `message` (role, content, tool_calls) stored in DB.
- [ ] Endpoint: POST message with optional `pack_id`; stream or non-stream response; backend passes conversation + pack context to Orchestrator.

### Context assembly

- [ ] When `pack_id` is set: load active Brand OS, Marketing Plan, Campaign (goal, CTA, angles), conversion page status, plan horizon and inject into Orchestrator context so Klaro is pack-aware.

### Use / Preview / Apply

- [ ] **Use**: User request → Orchestrator runs tools → result is new version (e.g. Version B); user sees outcome.
- [ ] **Preview**: API returns proposed change (e.g. diff or payload) without committing; no DB write.
- [ ] **Apply**: User confirms; same tool run is executed and committed (new version, no overwrite).

### Version safety and memory

- [ ] All generation tools create a new version; never overwrite. UI can show “Version B created” and compare/activate.
- [ ] Conversation history persisted; at least last N turns + pack context available to Orchestrator.

### Phase 5 sign-off

- [ ] Chat works globally and with pack context; pack-scoped chat uses correct strategy/campaign/page data.
- [ ] Preview returns proposed changes; Apply creates Version B. No overwrite of existing versions.

---

## Phase 6: Frontend (parallel and post-backend)

**Goal**: Global and pack-scoped navigation, onboarding, all module UIs, and progressive disclosure.

### Stack and layout

- [ ] Next.js (App Router) in `frontend/`; Dockerfile and Makefile build/serve frontend (e.g. `npm run build`, `out` or Node serve).
- [ ] UI library in use (e.g. shadcn/ui or Radix); accessibility and progressive disclosure considered.

### Global navigation

- [ ] Command Center (Chat), Packs, Studio, Clients, Money, Exports, Settings, Help implemented (sidebar or top nav). Command Center opens Chat (global or pack-scoped by entry).

### Pack creation and onboarding

- [ ] “Start new Campaign Pack” → create pack → onboarding (max 6 questions). On submit: call backend to complete onboarding and trigger strategy generation; loading state then redirect to Pack Overview.

### Pack-scoped navigation

- [ ] Routes for: Overview, Brand OS, Marketing Plan, Brand Identity, Campaign, Conversion Page, Plan and Tracker, Posters and Flyers, Ad Factory, Proposal, Invoice, Proof Vault. Each loads the correct resource; active version and “Version B” shown where applicable, with compare/activate.

### Key UX

- [ ] Progressive disclosure: onboarding as wizard/stepper; per-module next actions (e.g. set CTA before Conversion Page).
- [ ] Version comparison: list versions, diff view, “Activate Version B” for Brand OS, Marketing Plan, Conversion Page.
- [ ] One CTA: Campaign UI has single CTA field; Conversion Page and ad previews reflect campaign CTA.
- [ ] Plan and Tracker screen explains 7/30/90 lock rules and what is editable vs locked.

### Integration

- [ ] All mutations (create pack, complete onboarding, publish page, generate assets, export) go through REST API. Chat uses streaming endpoint; Chat UI shows “Preview” and “Apply” when Klaro proposes changes.

### Phase 6 sign-off

- [ ] User can complete onboarding and land on Pack Overview; all pack-scoped sections load from API.
- [ ] Version compare/activate works; Chat with Preview/Apply works against backend.

---

## Phase 7: Reflection, observability, and hardening (weeks 22–24)

**Goal**: Reflection loop, observability, cost controls, and production readiness.

### Reflection

- [ ] Reflection triggers implemented: weekly checkpoint, CTA change, plan horizon unlock, manual (and low performance if signals exist).
- [ ] Orchestrator “reflection” flow: evaluate goal alignment, score angles, detect strategy drift, propose corrective actions. Outputs to episodic memory or decision log; no auto-activation of major pivots.
- [ ] Reflection implemented as dedicated tool or sub-graph invoked by Orchestrator when triggers fire.

### Observability

- [ ] Metrics: tool success rate, agent retry rate, goal alignment (if computed), plan coherence, angle effectiveness (when data exists), failure modes, latency. Loguru with structured fields; optional Prometheus/OTEL or log aggregator.
- [ ] Decision log queryable for debugging and audits.

### Cost and safety

- [ ] Max reasoning depth and max tool chain length configurable in Orchestrator; retry caps per tool. Optional token budget tracking. Preview-first generation where applicable.

### Multi-agent maturity

- [ ] Level 2 (Orchestrator + specialists, tool-only mutations) stable in production. Level 3 (reflective optimisation) enabled only after reflection loop is tested and safe.
- [ ] Documentation updated for “agentic completion” (A-PRD §12): mutations via tools, Orchestrator controls execution, reflection deterministic, decision log stored, goal objects drive optimisation, guardrails server-enforced.

### Phase 7 sign-off

- [ ] Reflection runs on configured triggers; proposals are logged, not auto-applied.
- [ ] Observability and limits are in place; agentic completion criteria are documented and met.

---

## Definition of done (overall)

- [ ] Pack lifecycle works end-to-end: create → onboard → strategy → campaign → page → assets → export.
- [ ] Strategy, page, and assets are versioned; Version B never overwrites.
- [ ] Conversion page publishes successfully with governance.
- [ ] Assets (poster, video) render successfully.
- [ ] Revenue workflow (proposal, invoice, reminders) functions.
- [ ] Launch Pack export bundles all selected deliverables.
- [ ] All mutations occur via tools; Orchestrator in control; decision log and reflection in place; guardrails server-enforced.
