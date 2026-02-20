# Klarnow Ai V0

**Klarnow AI v0.1 — Product Requirements**

<aside>
🔒

**Owner:** Goodness

**Primary builder:** Moyo

**Status:** Locked scope for v0.1 build (includes Studio: Video Ad Factory + Posters)

</aside>

---

### 1) Product summary

Klarnow AI is a chat-first execution engine that turns a business into a repeating 14-day sprint that helps the user:

- Publish a conversion page
- Generate assets (video and posters)
- Launch
- Capture leads
- Follow up
- Send proposals or invoices
- Check in
- Reload and repeat

**Core behaviour:** The Command Centre shows **one Next Action** only.

---

### 2) Goals and success metrics

**Product goal**

Make execution feel effortless and modern, while still making the user feel like they are building their brand with AI (not watching AI build it for them).

**Activation metrics (MVP)**

Activated when the user completes all three:

- Conversion page published
- Sprint created
- At least one asset generated (video or poster)

**Business outcome metrics (MVP)**

Value achieved when any one occurs:

- Lead captured
- Proposal sent
- Invoice generated

---

### 3) Target users

The product supports three business types with presets:

1. Product sellers (retail, wholesale, manufacturing)
2. Local services (appointments and calls)
3. Coaches and consultants (calls, retainers, programs)

Presets change:

- Recommended CTA
- Tone defaults
- Suggested pack type

Presets do not change the underlying product structure.

---

### 4) Non-goals for v0.1

Not shipping in v0.1:

- Drag-and-drop editors (page or design)
- Social publishing integrations
- Full automation builder
- Deep analytics dashboards
- Full replacement of [Cal.com](http://Cal.com) or MailerLite inside Klarnow AI (separate Israel build)

---

### 5) End-to-end user flow (locked)

#### Step 1: Landing (public)

User answers 3 questions only:

1. What do you sell?
2. Who is it for?
3. Where are you based?

System:

- Creates Pack draft
- Creates Sprint Day 0–14
- Routes to `/app`

#### Step 2: Day 0 setup (in app)

User completes required setup:

- Brand name
- Primary CTA
- USP

Optional:

- Proof

System marks Day 0 complete and unlocks Day 1.

#### Step 3: 14-day sprint execution

Each day has:

- AI output
- One user action
- Definition of done
- Gates to prevent skipping critical steps

#### Step 4: Weekly check-in and sprint reload

On Day 14, user completes check-in and chooses next move:

- Scale what worked
- Fix conversion leak
- Close and get paid

System automatically creates the next sprint.

---

### 6) Public landing page requirements

#### Page structure

- Top bar: Klarnow | Install | About | Sign in
- Hero headline: **Build a business people come back to.**
- Subline: **A 14-day sprint that helps you publish, capture leads, and get paid.**
- Centre stage: chat input plus **Create Campaign Pack** button
- Microcopy: Takes about 2 minutes. You can edit later.
- Soft DFY route below: Want it installed for you? Apply →

#### Landing onboarding script (3 questions only)

- Q1: “What do you sell? Say it in one sentence.”
- Q2: “Who is it for?”
- Q3: “Where are you based? City + country.”

#### Backend writes from landing

- offer_one_liner_raw
- target_audience_raw
- location_raw

#### On completion

- Create Workspace (guest allowed)
- Create Pack draft
- Create Sprint (Day 0–14)
- Route to `/app`

---

### 7) App IA and screens (v0.1)

Minimum screens:

1. Command Centre (Home)
2. Pack Summary (read, edit via chat)
3. Conversion Page (preview, edit via chat, publish)
4. Sprint overview (day list)
5. Day detail (checklist + Studio access)
6. Studio (Video and Posters only)
7. Leads (list + detail)
8. Proposals (list + detail)
9. Invoices (list + detail)
10. Weekly check-in

---

### 8) Command Centre (core screen)

#### Layout requirements

- Thin top strip: Pack name, Day X of 14, date
- Hero: **Next Action** (one primary CTA button)
- Max 3 suggestion chips
- Minimal right tracker:
    - Today tasks (max 3)
    - Sprint dots (Day 0–14)
    - Current date

#### Next Action priority (locked)

1. Missed call or hot lead follow-up due
2. New lead not contacted
3. Follow-up overdue
4. Proposal pending
5. Invoice pending
6. Today’s sprint build step

Rule: If a lead action is due, it overrides build tasks until cleared or snoozed.

---

### 9) Pack model (minimum required fields)

Pack stores:

- brand_name
- offer_one_liner
- target_audience
- location_city
- location_country
- primary_cta

USP fields:

- usp_category
- usp_statement
- usp_proof
- usp_locked_line

Proof (optional):

- proof_types[]
- proof_text

Sprint drivers:

- primary_pain (Day 2)
- primary_outcome (Day 2)
- hero_angle (Day 3)

System inferred:

- business_type (product | service | coach)
- pack_type (Enquiries | Quotes | Sales)

---

### 10) Day 0 setup (in app, locked)

#### Day 0 Next Action

Finish setup (3 required + 1 optional)

Chips:

1. Brand name (required)
2. Primary CTA (required, suggested)
3. USP (required)
4. Proof (optional)

Day 0 completion requires: Brand name + CTA + USP.

#### USP prompt (required, simple language)

Prompt 1: “Why should someone choose you over the obvious alternatives?”

Options: Faster | More reliable | Better quality | More specialised | Better experience | Better value | Other

Prompt 2: “What proof point makes that true?”

Lock line generated:

`{usp_statement} — proven by {usp_proof}.`

---

### 11) 14-day sprint (v0.1 day cards)

Each day includes AI output + one user action + definition of done.

- **Day 1: Offer lock**
    - AI: rewrites offer into a clear promise + CTA line
    - User: confirms it is accurate and believable
    - Done: offer locked
- **Day 2: Audience lock**
    - AI: drafts pains and outcomes
    - User: selects one primary pain and one primary outcome
    - Done: pain and outcome saved
- **Day 3: Page draft**
    - AI: generates conversion page draft (fixed template)
    - User: selects hero angle (speed | quality | specialist | value)
    - Done: page draft exists
- **Day 4: Publish gate**
    - AI: finalises page
    - User: publishes and tests CTA on phone
    - Gate: traffic locked until page is live
    - Done: live URL saved
- **Day 5: Asset generation (Studio required)**
    - User must generate at least one asset:
        - Video set (A/B/C) **or**
        - Poster set (A/B/C)
    - Done: at least one asset exists in workspace
- **Day 6: Launch**
    - AI: launch checklist
    - User: posts or runs traffic and logs where
    - Done: launch logged
- **Day 7: Capture test**
    - AI: enables leads table
    - User: creates a test lead and confirms it appears
    - Done: test lead exists in Leads
- **Day 8: Follow-up rules**
    - AI: loads 3-touch follow-up templates
    - User: sets response rule (example: respond within 10 minutes during hours)
    - Done: response rule saved, reminders enabled
- **Day 9: Lead handling**
    - AI: suggests next action per lead
    - User: follows up with at least one lead and updates status
    - Done: at least one lead moved forward
- **Day 10: Offer tightening**
    - AI: suggests one improvement
    - User: chooses one change or confirms keep as is
    - Done: offer updated or confirmed
- **Day 11: Proposal create (if needed)**
    - AI: proposal draft
    - User: adds one real delivery detail (timeline, terms, next step)
    - Done: proposal ready or marked not needed
- **Day 12: Proposal send (if needed)**
    - AI: send copy
    - User: marks proposal sent
    - Done: sent or marked not needed
- **Day 13: Invoice (if needed)**
    - AI: invoice from accepted proposal only
    - User: confirms payment terms and sends invoice
    - Done: invoice sent or marked not needed
- **Day 14: Weekly check-in and reload**
    - AI: 5 check-in questions + recommendation
    - User: chooses next move (scale | fix leak | close and get paid)
    - Done: Sprint 2 created automatically

---

### 12) Conversion page module (v0.1)

Template sections (fixed):

- Hero
- Proof
- How it works
- FAQs
- CTA

Editing method:

- Chat edits only (no drag editor)

Publish requirement:

- System generates a live URL

Gate:

- Traffic steps blocked until page is published

---

### 13) Leads and follow-up (v0.1)

#### Leads fields (minimum)

- Name
- Phone
- Email (optional)
- Source
- Status
- Summary
- Next action
- Pack link

#### Lead statuses (locked)

New, Contacted, Booked, No answer, Won, Lost

#### Follow-up system (no builder)

Task-driven, template-driven.

Default cadence:

- Touch 1 now
- Touch 2 after 24 hours
- Touch 3 after 72 hours

After 3 attempts: mark cold.

Hard rule: No lead exists without a status and a next action task.

---

### 14) Proposal and invoice (v0.1)

Proposal statuses:

- Draft
- Sent
- Opened
- Accepted

Invoice rule:

- Invoice can only be created from an Accepted proposal.

Invoice statuses:

- Draft
- Sent
- Paid
- Overdue

Supports:

- Deposit line
- Final payment line

---

### 15) Studio module (v0.1)

Studio contains only:

1. Ad Factory (Video)
2. Posters generator

No editor. Generate, preview, download, regenerate.

#### 15A) Ad Factory (Video) V1 spec

**Purpose**

Generate 3 meaningfully different video variants so output is not “same video, different words”.

**Input object: BrandBrief**

Derived from Pack + user selections.

Required BrandBrief fields:

- business_name
- offer
- audience
- location (or online)
- primary_outcome
- proof_assets
- tone
- face_on_camera
- price_position
- cta_action
- cta_destination

User selections (3 only):

1. template_family: kinetic_text | problem_solution | benefits_list | objection_rebuttal | testimonial_style
2. style: face_led | faceless | product_shots
3. proof_selection: reviews | process | portfolio | founder_story | none

**Output per variant A/B/C**

- core_concept
- hook_line
- script_15s and script_30s
- 8-shot list
- on-screen text per shot
- NanoBanana prompts per shot
- Kling prompt 15s and 30s

Optional:

- MP4 URL (if rendering enabled)

**Pipeline (locked)**

- Engine 0: Normaliser
- Engine 1: Context Builder
- Engine 2: Variation Controller
- Validator pass 1
- Engine 3: Script Writer
- Validator pass 2 + Claims gate
- Engine 4: Visual System
- Engine 5: Kling Assembler
- Optional renderer service (job queue)

**Variant validator rules (locked)**

- A, B, C must have different path
- A, B, C must have different hook_type
- C must be offer_smash
- If face_on_camera = false, talking_head_authority is forbidden
- No repeated hook lines across variants
- One CTA action only across all variants
- No invented stats, no exaggerated claims

**Compliance rules (locked)**

- Captions always on
- One CTA only, repeated mid and end
- No “guaranteed”, “instant”, “cure”, “best in the world”
- No invented numbers

**UI requirements**

- Generate Video Ads (3 variants)
- Show engine progress status
- Always return scripts and prompts even if renderer fails
- Regenerate a single variant without regenerating all
- Cache by BrandBrief hash + selections + version

#### 15B) Posters generator V1 spec

**Purpose**

Generate 3 poster variants aligned to offer and CTA without an editor.

**Input: PosterBrief**

Derived from Pack:

- business_name
- offer_one_liner
- usp_locked_line
- primary_cta
- cta_destination
- proof_line (optional)
- tone
- business_type
- format (default 4:5, optional A4)

User selects:

- poster_template: offer | proof | objection
- format: 4:5 | A4

**Output**

- 3 variants A/B/C
- PNG export
- PDF export

**Variant rule (locked)**

Only one variable changes per variant:

- A changes headline framing
- B changes layout style
- C changes proof emphasis

Everything else identical.

**Quality rules**

- One CTA only
- Safe margins
- High-contrast text
- No clutter
- Uses brand kit if available, otherwise minimal default palette and type

**UI requirements**

- Generate Posters (3 variants)
- Thumbnail preview
- Download PNG or PDF
- Regenerate variant only

---

### 16) Data model (minimum)

Required objects:

- User
- Workspace
- Pack
- Sprint
- DayCard
- Task
- Page
- Lead
- Interaction
- Proposal
- Invoice
- Asset
- AdFactoryJob
- PosterJob

Asset fields:

- type: video | poster | post_copy
- variant_label: A | B | C
- content: scripts, prompts, files
- render_status (video)
- links back to: account_id, pack_id, sprint_id, day_id

---

### 17) Gates (locked)

- Page must be published before traffic and launch steps unlock.
- At least one asset must be generated before launch.
- Leads and overdue follow-ups override build steps in Next Action.

---

### 18) Build order (locked)

1. Pack + Sprint engine + state machine
2. Next Action engine + task queue
3. Command Centre UI
4. Day 0 setup (Brand name, CTA, USP)
5. Conversion page generator + publish
6. Posters generator (V1)
7. Ad Factory pipeline (scripts and prompts first, renderer optional)
8. Leads + follow-up tasks/templates
9. Proposals + invoices
10. Day 14 check-in + sprint reload
11. Caching, regenerate variant, polish

---

### 19) Definition of done (MVP acceptance criteria)

MVP is done when a user can:

1. Complete 3-question landing
2. Land in app with Pack + Sprint created
3. Complete Day 0 setup (brand name + CTA + USP)
4. Generate and publish conversion page (live URL exists)
5. Generate at least one asset (video set or poster set)
6. Log launch
7. Capture a lead (manual or test)
8. Follow up using templates and task queue
9. Create proposal and mark accepted
10. Create invoice and mark paid
11. Complete Day 14 check-in
12. Sprint reload creates Sprint 2 automatically

---

### 20) QA run-sheet (reference)

Use the 30-minute end-to-end QA checklist:

- Landing flow
- Day 0 setup completion
- Publish gate
- Asset generation
- Launch logging
- Lead creation and task priority
- Proposal → invoice rule
- Sprint reload

---

### 21) Open decisions (not blockers)

1. Email capture moment: after pack creation vs before publish
2. Whether MP4 rendering is enabled in v0.1 or shipped as prompts only
3. Default platform target for Kling prompts (Meta Reels vs TikTok vs Shorts)