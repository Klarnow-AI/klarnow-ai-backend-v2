import { api } from "@/lib/http";
import type {
  SprintRead,
  SprintDayDetail,
  SprintTodayTasksRead,
  TodayTaskToggleBody,
} from "@/types/api-types";

const PACKS_PREFIX = "/api/v1/packs";

export type SuggestDayResponse = {
  offer_one_liner?: string | null;
  primary_pain?: string | null;
  primary_outcome?: string | null;
  pitch_script?: string | null;
};

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
    userSelections?: Record<string, string>
  ) =>
    api<SprintRead>(
      `${PACKS_PREFIX}/${packId}/sprint/${sprintId}/day/${dayNumber}/complete`,
      { 
        method: "POST",
        body: userSelections ? JSON.stringify({ user_selections: userSelections }) : undefined,
      }
    ),

  checkIn: (packId: string, sprintId: string) =>
    api<SprintRead>(
      `${PACKS_PREFIX}/${packId}/sprint/${sprintId}/check-in`,
      { method: "POST" }
    ),

  createSprint: (packId: string) =>
    api<SprintRead>(`${PACKS_PREFIX}/${packId}/sprint`, {
      method: "POST",
      body: JSON.stringify({}),
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
    api<{ suggestion: string }>(
      `${PACKS_PREFIX}/${packId}/sprint/suggest-field`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),
};
