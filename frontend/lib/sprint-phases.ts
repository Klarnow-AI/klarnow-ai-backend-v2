/**
 * Phase mapping for 14-day sprint. Days 0–14 are grouped into 4 phases.
 */
export type SprintPhase = {
  id: string;
  label: string;
  dayNumbers: number[];
};

export const SPRINT_PHASES: SprintPhase[] = [
  {
    id: "clarity-confidence",
    label: "Clarity & Confidence",
    dayNumbers: [0, 1, 2, 3],
  },
  {
    id: "traffic-assets",
    label: "Traffic & Assets",
    dayNumbers: [4, 5, 6, 7],
  },
  {
    id: "pipeline-followup",
    label: "Pipeline & Follow-up",
    dayNumbers: [8, 9, 10, 11],
  },
  {
    id: "close-revenue",
    label: "Close & Revenue",
    dayNumbers: [12, 13, 14],
  },
];

export const DAY_TITLES: string[] = [
  "Foundation",
  "Offer",
  "USP + Audience",
  "Confidence Script",
  "Ad Factory",
  "Posters",
  "Conversion Destination",
  "Publish / Confirm",
  "Response Rules",
  "Follow-up",
  "Fix the Leak",
  "Close Path",
  "Close Conversations",
  "Invoice / Payment",
  "Check-in",
];

export function getPhaseForDay(dayNumber: number): SprintPhase | undefined {
  return SPRINT_PHASES.find((p) => p.dayNumbers.includes(dayNumber));
}
