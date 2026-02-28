"use client";

import { useRef } from "react";
import { chat as chatApi } from "@/api_requests/chat";
import {
  isStreamingPlaceholder,
  streamingPlaceholderId,
} from "@/app/(dashboard)/chat/helpers";
import type { Message } from "@/types/api-types";

type SendMode = "use" | "preview" | "apply";

type UseChatStreamOptions = {
  input: string;
  setInput: (value: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setLoading: (value: boolean) => void;
  setStreamingContent: (value: string) => void;
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
  ) {
    const cid = await ensureConversation();
    if (!cid) return;
    const content =
      contentOverride ??
      (mode === "apply" && !input.trim() ? "Apply the changes." : input);
    if (mode !== "apply" && !content.trim()) return;

    setStopTriggered(false);
    const controller = new AbortController();
    abortControllerRef.current = controller;
    streamingContentRef.current = "";

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      conversation_id: cid,
      role: "user",
      content,
      tool_calls: null,
      tool_results: null,
      is_preview: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    if (!contentOverride) setInput("");
    setLoading(true);
    setStreamingContent("");

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
    setMessages((prev) => [...prev, assistantPlaceholder]);

    try {
      const res = await chatApi.sendMessage(
        cid,
        {
          content,
          mode,
          apply_to_message_id: applyToId ?? undefined,
        },
        true,
        controller.signal,
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail || "Failed to send");
      }
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
          let data: string | null = null;
          for (const line of part.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) data = line.slice(5).trim();
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
                preview?: boolean;
                error?: string;
              };
              if (payload.error) throw new Error(payload.error);
              const finalContent = payload.assistant_content ?? accumulated;
              setMessages((prev) =>
                prev.map((m) =>
                  isStreamingPlaceholder(m.id)
                    ? {
                        ...m,
                        id: payload.message_id ?? m.id,
                        content: finalContent,
                        tool_calls: payload.tool_calls ?? null,
                        tool_results: payload.tool_results ?? null,
                        is_preview: payload.preview ?? false,
                      }
                    : m,
                ),
              );
              setStreamingContent("");
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
            }
            break;
          }
          if (event === "error" && data) {
            try {
              const parsed = JSON.parse(data) as { error?: string };
              throw new Error(parsed.error ?? "Stream error");
            } catch (error) {
              onError(error instanceof Error ? error.message : "Stream error");
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id)),
              );
              setStreamingContent("");
            }
            break;
          }
        }
      }
    } catch (error) {
      const isAbort = error instanceof Error && error.name === "AbortError";
      if (isAbort) {
        const finalContent = streamingContentRef.current || "(stopped)";
        setMessages((prev) =>
          prev.map((m) =>
            isStreamingPlaceholder(m.id)
              ? {
                  ...m,
                  id: `stopped-${m.id}`,
                  content: finalContent,
                }
              : m,
          ),
        );
        setStreamingContent("");
      } else {
        onError(error instanceof Error ? error.message : "Something went wrong");
        setMessages((prev) => prev.filter((m) => !isStreamingPlaceholder(m.id)));
        setStreamingContent("");
      }
    } finally {
      abortControllerRef.current = null;
      setLoading(false);
      setStopTriggered(false);
    }
  }

  function handleStop() {
    if (stopTriggered) return;
    setStopTriggered(true);
    abortControllerRef.current?.abort();
  }

  return { send, handleStop };
}

