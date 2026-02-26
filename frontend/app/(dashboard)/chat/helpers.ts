import type { DayQuestionContext } from "@/types/api-types";

/** In-flight assistant message id prefix; we show streamingContent for it. */
export function streamingPlaceholderId(): string {
  return `streaming-${Date.now()}`;
}

export function isStreamingPlaceholder(id: string): boolean {
  return id.startsWith("streaming-");
}

export function buildChatUrl(cid: string, pack?: string, day?: number): string {
  const params = new URLSearchParams();
  params.set("c", cid);
  if (pack) params.set("pack", pack);
  if (day !== undefined && day >= 0 && day <= 3) params.set("day", String(day));
  return `/chat?${params.toString()}`;
}

export function buildNewChatUrl(pack?: string): string {
  return pack ? `/chat?pack=${pack}` : "/chat";
}

/** Build chat URL with pack and optional day (0-3) for Day 0-3 flow. */
export function buildChatUrlWithDay(packId: string, day: number): string {
  const params = new URLSearchParams();
  params.set("pack", packId);
  if (day >= 0 && day <= 3) {
    params.set("day", String(day));
  }
  return `/chat?${params.toString()}`;
}

/** Extract DayQuestionContext from an assistant message with ask_day_question tool result. */
export function getQuestionContextFromMessage(message: {
  role: string;
  tool_calls?: unknown;
  tool_results?: unknown;
}): DayQuestionContext | null {
  if (message.role !== "assistant") return null;
  const toolCalls = Array.isArray(message.tool_calls)
    ? message.tool_calls
    : [];
  const call = toolCalls.find(
    (tc: { function?: { name?: string } }) =>
      tc?.function?.name === "ask_day_question"
  );
  if (!call) return null;
  const callId = (call as { id?: string }).id;
  if (!callId) return null;

  const results = message.tool_results;
  let resultObj: unknown = null;
  if (results && typeof results === "object") {
    const r = results as
      | { results?: Array<{ tool_call_id?: string; result?: unknown }> }
      | Array<{ tool_call_id?: string; result?: unknown }>;
    const arr = Array.isArray(r) ? r : r.results;
    if (Array.isArray(arr)) {
      const match = arr.find((x) => x.tool_call_id === callId);
      resultObj = match?.result;
    }
  }
  if (!resultObj || typeof resultObj !== "object") return null;
  const r = resultObj as Record<string, unknown>;
  const chips = Array.isArray(r.suggestion_chips)
    ? r.suggestion_chips
    : [];
  return {
    field_key: typeof r.field_key === "string" ? r.field_key : "",
    input_placeholder:
      typeof r.input_placeholder === "string" ? r.input_placeholder : undefined,
    input_type: ["input", "textarea", "choice"].includes(
      r.input_type as string
    )
      ? (r.input_type as "input" | "textarea" | "choice")
      : undefined,
    suggestion_chips: chips
      .filter(
        (c): c is { label: string; value: string } =>
          c &&
          typeof c === "object" &&
          typeof (c as { label?: unknown }).label === "string" &&
          typeof (c as { value?: unknown }).value === "string"
      )
      .map((c) => ({ label: c.label, value: c.value })),
    show_resuggest: r.show_resuggest === true,
  };
}
