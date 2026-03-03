import type { Message } from "@/types/api-types";

function randomClientSuffix(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function transientMessageId(prefix: string): string {
  return `${prefix}-${randomClientSuffix()}`;
}

/** In-flight assistant message id prefix; we show streamingContent for it. */
export function streamingPlaceholderId(): string {
  return transientMessageId("streaming");
}

export function isStreamingPlaceholder(id: string): boolean {
  return id.startsWith("streaming-");
}

export function dedupeMessagesById(messages: Message[]): Message[] {
  const seen = new Set<string>();
  const deduped: Message[] = [];
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (seen.has(message.id)) continue;
    seen.add(message.id);
    deduped.push(message);
  }
  return deduped.reverse();
}

export function buildChatUrl(cid: string, pack?: string): string {
  const params = new URLSearchParams();
  params.set("c", cid);
  if (pack) params.set("pack", pack);
  return `/chat?${params.toString()}`;
}

export function buildNewChatUrl(pack?: string): string {
  return pack ? `/chat?pack=${pack}` : "/chat";
}
