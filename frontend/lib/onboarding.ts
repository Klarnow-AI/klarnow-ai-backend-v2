/** Onboarding flow: new vs existing brand (chat-first). */

/** First message: branch on existing vs new brand. */
export const FIRST_MESSAGE =
  "Let's get you more calls and bookings. Do you already have a brand?";

/** Path A (existing brand): input type step message. */
export const PATH_A_INPUT_TYPE_MESSAGE =
  "Share your brand: paste your website URL, paste your services copy, or upload a logo.";

/** Path B (new brand): ask brand name. */
export const PATH_B_BRAND_NAME_MESSAGE = "What's your brand name?";

/** Path B: ask vibe chips. */
export const PATH_B_VIBE_MESSAGE =
  "Pick a few words that describe your brand vibe (we'll use these for look and feel).";

/** Blocker questions (asked after Path A extract or Path B generate). Keys become q1..q5 in onboarding_answers. */
export const BLOCKER_QUESTIONS = [
  { key: "q1", label: "Who is your target audience?" },
  { key: "q2", label: "What is your primary marketing goal for this campaign?" },
  { key: "q3", label: "Which channel will you focus on first?" },
  { key: "q4", label: "What makes your offer unique?" },
  { key: "q5", label: "Any specific constraints or preferences we should know?" },
] as const;

export const BLOCKER_COUNT = BLOCKER_QUESTIONS.length;

/** Vibe chip options for Path B (new brand). */
export const VIBE_CHIP_OPTIONS = [
  "Professional",
  "Bold",
  "Minimal",
  "Playful",
  "Luxury",
  "Friendly",
  "Modern",
  "Classic",
  "Creative",
  "Trustworthy",
] as const;

/** Legacy: max onboarding answer keys (backend allows 20). */
export const ONBOARDING_MAX = 20;

/** Legacy: linear question list for backward compatibility (blockers only). */
export const QUESTIONS = BLOCKER_QUESTIONS.map((q) => q.label);

/** Pack type step (after last blocker). MVP routing: Enquiries, Quotes, Sales. */
export const PACK_TYPE_STEP_LABEL = "What's the goal for this pack?";
export const PACK_TYPE_OPTIONS = [
  {
    value: "enquiries",
    label: "Enquiries",
    description: "Get leads and enquiries. Proposal optional.",
  },
  {
    value: "quotes",
    label: "Quotes",
    description: "Send quotes and win work. Proposal mandatory.",
  },
  {
    value: "sales",
    label: "Sales",
    description: "Sell directly. CTA is checkout; minimal capture.",
  },
] as const;
