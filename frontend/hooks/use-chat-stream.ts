"use client";

import { useRef } from "react";
import { chat as chatApi } from "@/api_requests/chat";
import {
  dedupeMessagesById,
  isStreamingPlaceholder,
  streamingPlaceholderId,
  transientMessageId,
} from "@/app/(dashboard)/chat/helpers";
import { getApiError, isRequestCancelled } from "@/lib/http";
import type { ChatAttachment, Message } from "@/types/api-types";

type SendMode = "use" | "preview" | "apply";
export type StreamStatus =
  | "idle"
  | "thinking"
  | "tool_execution"
  | "finalizing"
  | "responding";

type ChatActionChip = {
  label: string;
  href: string;
};

function isStreamStatus(value: string): value is StreamStatus {
  return (
    value === "idle" ||
    value === "thinking" ||
    value === "tool_execution" ||
    value === "finalizing" ||
    value === "responding"
  );
}

function isObjectLike(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeActionChips(value: unknown): ChatActionChip[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => isObjectLike(item))
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }))
    .filter((chip) => chip.label.length > 0 && chip.href.length > 0);
}

function mergeToolResultsWithActions(
  toolResults: unknown,
  actionChips: unknown,
): unknown {
  const chips = normalizeActionChips(actionChips);
  if (chips.length === 0) return toolResults ?? null;
  if (isObjectLike(toolResults)) return { ...toolResults, actions: chips };
  return { actions: chips };
}

function normalizeStreamError(payload: unknown): Error {
  if (isObjectLike(payload)) {
    const apiError = getApiError(payload, "Chat request failed.");
    return apiError;
  }
  if (typeof payload === "string" && payload.trim()) {
    return new Error(payload.trim());
  }
  return new Error("Chat request failed.");
}

type UseChatStreamOptions = {
  input: string;
  setInput: (value: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setLoading: (value: boolean) => void;
  setStreamingContent: (value: string) => void;
  setStreamStatus: (value: StreamStatus) => void;
  stopTriggered: boolean;
  setStopTriggered: (value: boolean) => void;
  setPreviewMessageId?: (value: string | null) => void;
  setApplyTargetId?: (value: string | null) => void;
  ensureConversation: () => Promise<string | null>;
  loadMessages?: (conversationId: string) => Promise<void>;
  onError: (message: string) => void;
};

export function useChatStream(options: UseChatStreamOptions) {
  const {
    input,
    setInput,
    setMessages,
    setLoading,
    setStreamingContent,
    setStreamStatus,
    stopTriggered,
    setStopTriggered,
    setPreviewMessageId,
    setApplyTargetId,
    ensureConversation,
    loadMessages,
    onError,
  } = options;
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");

  async function send(
    mode: SendMode,
    applyToId?: string | null,
    contentOverride?: string,
    attachmentsOverride: ChatAttachment[] = [],
  ) {
    const cid = await ensureConversation();
    if (!cid) return;
    const attachmentIds = attachmentsOverride.map((a) => a.id);
    const hasAttachments = attachmentIds.length > 0;
    const content =
      contentOverride ??
      (mode === "apply" && !input.trim()
        ? "Apply the changes."
        : input.trim() || (hasAttachments ? "Use the attached files as context." : input));
    if (mode !== "apply" && !content.trim() && !hasAttachments) return;

    setStopTriggered(false);
    const controller = new AbortController();
    abortControllerRef.current = controller;
    streamingContentRef.current = "";

    const userMsg: Message = {
      id: transientMessageId("user"),
      conversation_id: cid,
      role: "user",
      content,
      tool_calls: null,
      tool_results: null,
      attachments:
        attachmentsOverride.length > 0
          ? attachmentsOverride.map((item) => ({
              id: item.id,
              file_name: item.file_name,
              content_type: item.content_type,
              size_bytes: item.size_bytes,
              has_text_content: item.has_text_content,
            }))
          : null,
      is_preview: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => dedupeMessagesById([...prev, userMsg]));
    if (!contentOverride) setInput("");
    setLoading(true);
    setStreamingContent("");
    setStreamStatus("thinking");

    const assistantPlaceholder: Message = {
      id: streamingPlaceholderId(),
      conversation_id: cid,
      role: "assistant",
      content: "",
      tool_calls: null,
      tool_results: null,
      is_preview: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => dedupeMessagesById([...prev, assistantPlaceholder]));

    try {
      const res = await chatApi.sendMessage(
        cid,
        {
          content,
          mode,
          apply_to_message_id: applyToId ?? undefined,
          attachment_ids: hasAttachments ? attachmentIds : undefined,
        },
        true,
        controller.signal,
      );
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");
      let buffer = "";
      let accumulated = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          let event: string | null = null;
          const dataLines: string[] = [];
          for (const line of part.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
          }
          const data = dataLines.length > 0 ? dataLines.join("\n") : null;
          if (event === "status" && data) {
            try {
              const parsed = JSON.parse(data) as { phase?: string };
              if (
                typeof parsed.phase === "string" &&
                isStreamStatus(parsed.phase)
              ) {
                setStreamStatus(parsed.phase);
                if (parsed.phase === "finalizing") {
                  accumulated = "";
                  streamingContentRef.current = "";
                  setStreamingContent("");
                }
              }
            } catch {
              /* ignore */
            }
          }
          if (event === "chunk" && data) {
            try {
              const parsed = JSON.parse(data) as { delta?: string };
              if (typeof parsed.delta === "string") {
                accumulated += parsed.delta;
                streamingContentRef.current = accumulated;
                setStreamingContent(accumulated);
              }
            } catch {
              /* ignore */
            }
          }
          if (event === "done" && data) {
            try {
              const payload = JSON.parse(data) as {
                message_id?: string;
                assistant_content?: string;
                tool_calls?: unknown;
                tool_results?: unknown;
                action_chips?: unknown;
                references?: unknown;
                preview?: boolean;
                error?: unknown;
              };
              if (payload.error) throw normalizeStreamError(payload.error);
              const finalContent = payload.assistant_content ?? accumulated;
              const mergedToolResults = mergeToolResultsWithActions(
                payload.tool_results,
                payload.action_chips,
              );
              setMessages((prev) =>
                dedupeMessagesById(
                  prev.map((m) =>
                    isStreamingPlaceholder(m.id)
                      ? {
                          ...m,
                          id: payload.message_id ?? m.id,
                          content: finalContent,
                          tool_calls: payload.tool_calls ?? null,
                          tool_results: mergedToolResults,
                          is_preview: payload.preview ?? false,
                        }
                      : m,
                  ),
                ),
              );
              setStreamingContent("");
              setStreamStatus("idle");
              if (
                payload.preview &&
                Array.isArray(payload.tool_calls) &&
                payload.tool_calls.length
              ) {
                setPreviewMessageId?.(payload.message_id ?? null);
                setApplyTargetId?.(payload.message_id ?? null);
                await loadMessages?.(cid);
              }
            } catch (error) {
              onError(
                error instanceof Error ? error.message : "Something went wrong",
              );
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id)),
              );
              setStreamingContent("");
              setStreamStatus("idle");
            }
            break;
          }
          if (event === "error" && data) {
            try {
              throw normalizeStreamError(JSON.parse(data) as unknown);
            } catch (error) {
              onError(error instanceof Error ? error.message : "Stream error");
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id)),
              );
              setStreamingContent("");
              setStreamStatus("idle");
            }
            break;
          }
        }
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        const finalContent = streamingContentRef.current || "(stopped)";
        setMessages((prev) =>
          dedupeMessagesById(
            prev.map((m) =>
              isStreamingPlaceholder(m.id)
                ? {
                    ...m,
                    id: `stopped-${m.id}`,
                    content: finalContent,
                  }
                : m,
            ),
          ),
        );
        setStreamingContent("");
        setStreamStatus("idle");
      } else {
        onError(error instanceof Error ? error.message : "Something went wrong");
        setMessages((prev) => prev.filter((m) => !isStreamingPlaceholder(m.id)));
        setStreamingContent("");
        setStreamStatus("idle");
      }
    } finally {
      abortControllerRef.current = null;
      setLoading(false);
      setStopTriggered(false);
      setStreamStatus("idle");
    }
  }

  function handleStop() {
    if (stopTriggered) return;
    setStopTriggered(true);
    abortControllerRef.current?.abort();
  }

  return { send, handleStop };
}
