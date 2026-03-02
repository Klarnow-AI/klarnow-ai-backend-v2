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

/** MVP flow: 4 steps only (3 questions + pack name). Keys match landing-complete API. */
export const MVP_STEP_KEYS = [
  "what_do_you_sell",
  "who_is_it_for",
  "where_are_you_based",
  "pack_name",
] as const;

export const MVP_QUESTIONS: {
  label: string;
  placeholder: string;
  subLabel?: string;
}[] = [
  {
    label: "What do you sell?",
    placeholder: "e.g. I help small shops get more foot traffic",
    subLabel: "One sentence. This drives everything.",
  },
  {
    label: "Who is it for?",
    placeholder: "e.g. Local retail owners",
    subLabel: "Describe your ideal customer.",
  },
  {
    label: "Where are you based?",
    placeholder: "e.g. Manchester, UK",
    subLabel: "City + country.",
  },
  {
    label: "What would you like to name this pack?",
    placeholder: "e.g. My Campaign Pack",
    subLabel: "This is your campaign pack name.",
  },
];

export const MVP_STEP_COUNT = MVP_QUESTIONS.length;

/** Generate pack name suggestion chips from the first 3 MVP answers. */
export function getPackNameSuggestionChips(
  answers: Record<string, string>,
): { label: string; value: string }[] {
  const offer = (answers.what_do_you_sell || "").trim();
  const audience = (answers.who_is_it_for || "").trim();
  const location = (answers.where_are_you_based || "").trim();
  const chips: { label: string; value: string }[] = [];
  if (audience)
    chips.push({
      label: `${audience} Campaign`,
      value: `${audience} Campaign`,
    });
  if (offer && location)
    chips.push({
      label: `${offer} - ${location}`,
      value: `${offer} - ${location}`,
    });
  if (offer)
    chips.push({ label: `My ${offer} Pack`, value: `My ${offer} Pack` });
  if (location)
    chips.push({
      label: `${location} Outreach`,
      value: `${location} Outreach`,
    });
  return chips.slice(0, 4);
}

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
