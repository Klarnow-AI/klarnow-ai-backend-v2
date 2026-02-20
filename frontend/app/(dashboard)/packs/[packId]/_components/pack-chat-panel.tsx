"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { chat as chatApi } from "@/api_requests/chat";
import { me } from "@/api_requests/me";
import type { Message } from "@/types/api-types";
import type { NextAction } from "@/types/api-types";
import {
  ChatMessageList,
  ChatInputBlock,
} from "@/app/(dashboard)/chat/_components";
import {
  streamingPlaceholderId,
  isStreamingPlaceholder,
} from "@/app/(dashboard)/chat/helpers";

type SendMode = "use" | "preview" | "apply";

export function PackChatPanel({ packId }: { packId: string }) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [previewMessageId, setPreviewMessageId] = useState<string | null>(null);
  const [applyTargetId, setApplyTargetId] = useState<string | null>(null);
  const [stopTriggered, setStopTriggered] = useState(false);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");

  useEffect(() => {
    me.getNextAction(packId).then(setNextAction).catch(() => setNextAction(null));
  }, [packId]);

  useEffect(() => {
    if (!packId) return;
    chatApi
      .listConversations(packId)
      .then((res) => {
        if (res.items.length > 0) {
          const latest = res.items[0];
          setConversationId(latest.id);
        } else {
          setConversationId(null);
          setMessages([]);
        }
      })
      .catch(() => {
        setConversationId(null);
        setMessages([]);
      });
  }, [packId]);

  useEffect(() => {
    if (!conversationId) return;
    chatApi.getMessages(conversationId).then((res) => {
      setMessages((prev) => {
        if (
          res.items.length === 0 &&
          prev.some(
            (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-")
          )
        )
          return prev;
        return res.items;
      });
      const lastPreview = res.items.filter((m) => m.is_preview).pop();
      if (lastPreview) {
        setPreviewMessageId(lastPreview.id);
        setApplyTargetId(lastPreview.id);
      }
    });
  }, [conversationId]);

  async function ensureConversation(): Promise<string | null> {
    if (conversationId) return conversationId;
    try {
      const conv = await chatApi.createConversation(packId);
      setConversationId(conv.id);
      return conv.id;
    } catch {
      return null;
    }
  }

  async function loadMessages(cid: string) {
    const res = await chatApi.getMessages(cid);
    setMessages((prev) => {
      if (
        res.items.length === 0 &&
        prev.some(
          (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-")
        )
      )
        return prev;
      return res.items;
    });
    const lastPreview = res.items.filter((m) => m.is_preview).pop();
    if (lastPreview) {
      setPreviewMessageId(lastPreview.id);
      setApplyTargetId(lastPreview.id);
    }
  }

  async function send(mode: SendMode, applyToId?: string | null) {
    const cid = await ensureConversation();
    if (!cid) return;
    const content =
      mode === "apply" && !input.trim() ? "Apply the changes." : input;
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
    setInput("");
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
        controller.signal
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          (err as { detail?: string }).detail || "Failed to send"
        );
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
                    : m
                )
              );
              setStreamingContent("");
              if (
                payload.preview &&
                Array.isArray(payload.tool_calls) &&
                payload.tool_calls.length
              ) {
                setPreviewMessageId(payload.message_id ?? null);
                setApplyTargetId(payload.message_id ?? null);
                await loadMessages(cid);
              }
            } catch (e) {
              console.error(e);
              alert(e instanceof Error ? e.message : "Something went wrong");
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id))
              );
              setStreamingContent("");
            }
            break;
          }
          if (event === "error" && data) {
            try {
              const parsed = JSON.parse(data) as { error?: string };
              throw new Error(parsed.error ?? "Stream error");
            } catch (e) {
              console.error(e);
              alert(e instanceof Error ? e.message : "Stream error");
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id))
              );
              setStreamingContent("");
            }
            break;
          }
        }
      }
    } catch (e) {
      const isAbort = e instanceof Error && e.name === "AbortError";
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
              : m
          )
        );
        setStreamingContent("");
      } else {
        console.error(e);
        alert(e instanceof Error ? e.message : "Something went wrong");
        setMessages((prev) =>
          prev.filter((m) => !isStreamingPlaceholder(m.id))
        );
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    if (applyTargetId) {
      send("apply", applyTargetId);
      setApplyTargetId(null);
    } else {
      if (!input.trim()) return;
      send("use");
    }
  }

  function startNewChat() {
    setConversationId(null);
    setMessages([]);
    setStreamingContent("");
    setPreviewMessageId(null);
    setApplyTargetId(null);
  }

  const fullChatUrl = conversationId
    ? `/chat?pack=${packId}&c=${conversationId}`
    : `/chat?pack=${packId}`;

  return (
    <div className="flex flex-col flex-1 min-h-0 rounded-2xl border border-border bg-card overflow-hidden">
      <div className="shrink-0 px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Chat with Klaro
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={startNewChat}
            className="text-xs font-medium text-primary hover:underline"
          >
            New chat
          </button>
          <span className="text-muted-foreground">|</span>
          <Link
            href={fullChatUrl}
            className="text-xs font-medium text-primary hover:underline"
          >
            Open in full chat
          </Link>
        </div>
      </div>
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 flex flex-col">
          {messages.length === 0 && !loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-8 min-h-[140px]">
              <p className="text-sm font-medium text-foreground mb-1.5">
                Start a conversation
              </p>
              <p className="text-sm text-muted-foreground max-w-[280px] leading-relaxed">
                Ask Klaro anything about this pack—get suggestions, update your
                campaign, or plan your next steps.
              </p>
            </div>
          ) : (
            <ChatMessageList
              messages={messages}
              streamingContent={streamingContent}
              loading={loading}
              onApply={(id) => send("apply", id)}
            />
          )}
        </div>
        <div className="shrink-0 px-4 py-3 border-t border-border">
          <ChatInputBlock
            input={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            onPreview={() => send("preview")}
            onStop={handleStop}
            loading={loading}
            stopTriggered={stopTriggered}
            applyTargetId={applyTargetId}
            suggestionChips={nextAction?.actionChips}
          />
        </div>
      </div>
    </div>
  );
}
