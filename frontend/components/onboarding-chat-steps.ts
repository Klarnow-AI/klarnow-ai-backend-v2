import {
  BLOCKER_QUESTIONS,
  BLOCKER_COUNT,
  PACK_TYPE_STEP_LABEL,
} from "@/lib/onboarding";

export const STEP_PACK_NAME = 0;
export const STEP_BRAND_QUESTION = 1;
export const STEP_PATH_FIRST = 2;
export const STEP_PATH_SECOND = 3;
export const STEP_BLOCKERS_START = 4;
export const STEP_BLOCKERS_END = STEP_BLOCKERS_START + BLOCKER_COUNT - 1;
export const STEP_PACK_TYPE = STEP_BLOCKERS_END + 1;

/** MVP flow: 4 steps only (pack name + 3 questions). Keys match landing-complete API. */
export const MVP_STEP_KEYS = [
  "pack_name",
  "what_do_you_sell",
  "who_is_it_for",
  "where_are_you_based",
] as const;

export const MVP_QUESTIONS: { label: string; placeholder: string }[] = [
  {
    label: "What would you like to name this campaign pack?",
    placeholder: "e.g. My Campaign",
  },
  {
    label: "What do you sell? Say it in one sentence.",
    placeholder: "e.g. I help small shops get more foot traffic",
  },
  { label: "Who is it for?", placeholder: "e.g. Local retail owners" },
  {
    label: "Where are you based? City + country.",
    placeholder: "e.g. Manchester, UK",
  },
];

export const MVP_STEP_COUNT = MVP_QUESTIONS.length;

/** Extract question and helper text for form-focused UI */
export function getQuestionContent(
  step: number,
  hasExistingBrand: boolean,
): { question: string; helper?: string } {
  if (step === STEP_PACK_NAME) {
    return {
      question: "What would you like to name this campaign pack?",
      helper: "You can change this later",
    };
  }

  if (step === STEP_BRAND_QUESTION) {
    return {
      question: "Do you already have a brand?",
      helper: "Let's get you more calls and bookings",
    };
  }

  if (step === STEP_PATH_FIRST) {
    if (hasExistingBrand) {
      return {
        question: "Enter your website URL",
        helper: "We'll extract your brand information from your website",
      };
    }
    return {
      question: "What's your brand name?",
    };
  }

  if (step === STEP_PATH_SECOND) {
    return {
      question: "Pick words that describe your brand vibe",
      helper: "We'll use these for look and feel",
    };
  }

  if (step >= STEP_BLOCKERS_START && step <= STEP_BLOCKERS_END) {
    const blockerIndex = step - STEP_BLOCKERS_START;
    return {
      question: BLOCKER_QUESTIONS[blockerIndex].label,
    };
  }

  if (step === STEP_PACK_TYPE) {
    return {
      question: PACK_TYPE_STEP_LABEL,
      helper:
        "This determines your pack flow: enquiries, quotes, or direct sales.",
    };
  }

  return { question: "Loading..." };
}

