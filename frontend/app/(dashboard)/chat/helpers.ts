/** In-flight assistant message id prefix; we show streamingContent for it. */
export function streamingPlaceholderId(): string {
  return `streaming-${Date.now()}`;
}

export function isStreamingPlaceholder(id: string): boolean {
  return id.startsWith("streaming-");
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
