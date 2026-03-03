export type TaskActionKey =
  | "open_ad_factory"
  | "open_leads"
  | "open_posters"
  | "open_website"
  | "open_plan_tracker"
  | "open_chat"
  | "open_proposals"
  | "open_invoices"
  | "scroll_response_rules_editor";

export interface DayGuideTaskAction {
  type: "route" | "inline";
  key: TaskActionKey;
  ctaLabel: string;
}

export type ResolvedTaskAction =
  | { type: "route"; href: string }
  | { type: "inline"; targetId: string };

export function resolveTaskAction(
  packId: string,
  action: DayGuideTaskAction,
): ResolvedTaskAction | null {
  const safePackId = encodeURIComponent(packId);

  switch (action.key) {
    case "open_ad_factory":
      return { type: "route", href: `/packs/${safePackId}/ad-factory` };
    case "open_leads":
      return { type: "route", href: `/packs/${safePackId}/leads` };
    case "open_posters":
      return { type: "route", href: `/packs/${safePackId}/posters` };
    case "open_website":
      return { type: "route", href: `/packs/${safePackId}/website` };
    case "open_plan_tracker":
      return { type: "route", href: `/packs/${safePackId}/plan-tracker` };
    case "open_chat":
      return { type: "route", href: `/chat?pack=${safePackId}` };
    case "open_proposals":
      return { type: "route", href: `/packs/${safePackId}/proposal` };
    case "open_invoices":
      return { type: "route", href: `/packs/${safePackId}/invoice` };
    case "scroll_response_rules_editor":
      return { type: "inline", targetId: "response-rules-editor" };
    default:
      return null;
  }
}
