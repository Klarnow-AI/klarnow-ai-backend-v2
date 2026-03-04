# Klarnow AI — Frontend (Phase 6)

Next.js 14 (App Router), Tailwind CSS, Framer Motion. Modern AI-product aesthetic inspired by ChatGPT, ManusAI, Lovable, and Relume.

## Run locally

```bash
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_GOOGLE_CLIENT_ID
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Ensure the backend is running and `FRONTEND_URL` includes `http://localhost:3000` for CORS.

## Build

```bash
npm run build
npm run start
```

## Features

- **Auth**: Email/password, email login code, and Google sign-in (JWT stored in localStorage).
- **Global nav**: Command Center (Chat), Packs, Studio, Clients, Money, Exports, Settings, Help.
- **Packs**: List, create, onboarding wizard (max 6 questions), then Pack Overview.
- **Pack-scoped**: Overview, Brand OS, Marketing Plan, Campaign, Conversion Page, Plan & Tracker, Posters, Ad Factory, Proposal, Invoice, Proof Vault.
- **Chat**: Command Center with pack-scoped or global conversation. **Preview** (proposed tool_calls) and **Apply** (execute and create Version B).
- **UI**: Dark theme, motion, gradient accents, accessible components.
