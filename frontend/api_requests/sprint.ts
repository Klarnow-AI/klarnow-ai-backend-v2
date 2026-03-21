import { api, isAppRequestError } from "@/lib/http";
import {
  dispatchPackRefresh,
  type PackRefreshScope,
} from "@/lib/pack-refresh-events";
import type {
  SprintRead,
  SprintDayDetail,
  SprintTodayTasksRead,
  TodayTaskToggleBody,
} from "@/types/api-types";

const PACKS_PREFIX = "/api/v1/packs";
const SPRINT_REFRESH_SCOPES: PackRefreshScope[] = [
  "summary",
  "today-tasks",
  "next-action",
  "gates",
  "sprint",
];

export type SuggestDayResponse = {
  offer_one_liner?: string | null;
  primary_pain?: string | null;
  primary_outcome?: string | null;
  pitch_script?: string | null;
  source?: "ai" | "fallback";
  reason?: string | null;
};

export type SuggestFieldResponse = {
  suggestion: string;
  source?: "ai" | "fallback";
  reason?: string | null;
};

export function getSprintSuggestionErrorMessage(error: unknown): string {
  if (
    isAppRequestError(error) &&
    (error.kind === "service" || error.kind === "server")
  ) {
    return "Sprint AI suggestions are temporarily unavailable. Please try again.";
  }
  return error instanceof Error ? error.message : "Could not get suggestion";
}

type CompleteDayOptions = {
  suppressPackRefresh?: boolean;
};

function dispatchSprintRefresh(packId: string) {
  dispatchPackRefresh({
    packId,
    scopes: SPRINT_REFRESH_SCOPES,
  });
}

export const sprintApi = {
  getSprint: (packId: string) =>
    api<SprintRead | null>(`${PACKS_PREFIX}/${packId}/sprint`),

  getSprintDay: (packId: string, dayNumber: number) =>
    api<SprintDayDetail | null>(
      `${PACKS_PREFIX}/${packId}/sprint/day/${dayNumber}`
    ),

  getTodayTasks: (packId: string) =>
    api<SprintTodayTasksRead>(`${PACKS_PREFIX}/${packId}/sprint/today-tasks`),

  toggleTodayTask: (packId: string, body: TodayTaskToggleBody) =>
    api<SprintTodayTasksRead>(`${PACKS_PREFIX}/${packId}/sprint/today-tasks`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  completeDay: (
    packId: string,
    sprintId: string,
    dayNumber: number,
    userSelections?: Record<string, string>,
    options?: CompleteDayOptions,
  ) =>
    api<SprintRead>(
      `${PACKS_PREFIX}/${packId}/sprint/${sprintId}/day/${dayNumber}/complete`,
      {
        method: "POST",
        body: userSelections
          ? JSON.stringify({ user_selections: userSelections })
          : undefined,
      },
    ).then((result) => {
      if (!options?.suppressPackRefresh) {
        dispatchSprintRefresh(packId);
      }
      return result;
    }),

  checkIn: (packId: string, sprintId: string) =>
    api<SprintRead>(
      `${PACKS_PREFIX}/${packId}/sprint/${sprintId}/check-in`,
      { method: "POST" },
    ).then((result) => {
      dispatchSprintRefresh(packId);
      return result;
    }),

  createSprint: (packId: string) =>
    api<SprintRead>(`${PACKS_PREFIX}/${packId}/sprint`, {
      method: "POST",
      body: JSON.stringify({}),
    }).then((result) => {
      dispatchSprintRefresh(packId);
      return result;
    }),

  /** Suggested values for Day 1, 2, or 3 fields (pre-fill modals). */
  suggestDayFields: (
    packId: string,
    dayNumber: 1 | 2 | 3
  ) =>
    api<SuggestDayResponse>(
      `${PACKS_PREFIX}/${packId}/sprint/suggest-day/${dayNumber}`,
      { method: "POST" }
    ),

  /** Suggest or refine a single field (Refine with AI). */
  suggestField: (
    packId: string,
    body: {
      day: 1 | 2 | 3;
      field: string;
      current_value?: string | null;
    }
  ) =>
    api<SuggestFieldResponse>(
      `${PACKS_PREFIX}/${packId}/sprint/suggest-field`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),
};
