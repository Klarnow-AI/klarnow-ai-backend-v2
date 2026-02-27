"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { chat as chatApi } from "@/api_requests/chat";
import type { Message } from "@/types/api-types";
import {
  buildChatUrl,
  buildNewChatUrl,
  getQuestionContextFromMessage,
  isStreamingPlaceholder,
  streamingPlaceholderId,
} from "./helpers";
import { dayGuides } from "@/app/(dashboard)/packs/[packId]/plan-tracker/day/[dayNumber]/_data/dayGuides";
import {
  ChatMessageList,
  ChatInputBlock,
  ChatHistoryModal,
  ChatFab,
  NextActionBanner,
} from "./_components";
import { me } from "@/api_requests/me";
import type { NextAction } from "@/types/api-types";
import { useChatStore } from "./_store/chat-store";
import { useShallow } from "zustand/react/shallow";
import { toast } from "sonner";

type SendMode = "use" | "preview" | "apply";

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cFromUrl = searchParams.get("c");
  const packId = searchParams.get("pack") ?? undefined;
  const dayParam = searchParams.get("day");
  const dayContext: { day: number; title: string } | undefined =
    dayParam !== null
      ? (() => {
          const d = parseInt(dayParam, 10);
          if (Number.isInteger(d) && d >= 0 && d <= 3) {
            const guide = dayGuides[d as 0 | 1 | 2 | 3];
            return guide ? { day: d, title: guide.title } : undefined;
          }
          return undefined;
        })()
      : undefined;
  const [historyModalOpenState, setHistoryModalOpenState] = useState(false);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const [
    conversationId,
    messages,
    input,
    loading,
    streamingContent,
    previewMessageId,
    applyTargetId,
    historyList,
    historyLoading,
    stopTriggered,
    setConversationId,
    setMessages,
    setStreamingContent,
    setPreviewMessageId,
    setApplyTargetId,
    setHistoryList,
    setHistoryLoading,
    setInput,
    setLoading,
    setStopTriggered,
    resetForNewChat,
  ] = useChatStore(
    useShallow((s) => [
      s.conversationId,
      s.messages,
      s.input,
      s.loading,
      s.streamingContent,
      s.previewMessageId,
      s.applyTargetId,
      s.historyList,
      s.historyLoading,
      s.stopTriggered,
      s.setConversationId,
      s.setMessages,
      s.setStreamingContent,
      s.setPreviewMessageId,
      s.setApplyTargetId,
      s.setHistoryList,
      s.setHistoryLoading,
      s.setInput,
      s.setLoading,
      s.setStopTriggered,
      s.resetForNewChat,
    ]),
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");

  useEffect(() => {
    if (!historyModalOpenState) return;
    setHistoryLoading(true);
    chatApi
      .listConversations(packId)
      .then((res) => setHistoryList(res.items))
      .catch(() => setHistoryList([]))
      .finally(() => setHistoryLoading(false));
  }, [historyModalOpenState, packId, setHistoryList, setHistoryLoading]);

  useEffect(() => {
    if (cFromUrl) setConversationId(cFromUrl);
    else setConversationId(null);
  }, [cFromUrl, setConversationId]);

  useEffect(() => {
    me.getNextAction(packId ?? null)
      .then(setNextAction)
      .catch(() => setNextAction(null));
  }, [packId]);

  async function ensureConversation() {
    if (conversationId) return conversationId;
    const dayNum = dayParam !== null ? parseInt(dayParam, 10) : NaN;
    const dayCtx =
      Number.isInteger(dayNum) && dayNum >= 0 && dayNum <= 3
        ? dayNum
        : undefined;
    const conv = await chatApi.createConversation(packId, dayCtx);
    setConversationId(conv.id);
    router.replace(buildChatUrl(conv.id, packId, dayCtx));
    return conv.id;
  }

  async function loadMessages(cid: string) {
    const res = await chatApi.getMessages(cid);
    setMessages((prev) => {
      if (
        res.items.length === 0 &&
        prev.some(
          (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-"),
        )
      )
        return prev;
      return res.items;
    });
    const lastPreview = res.items.filter((m) => m.is_preview).pop();
    if (lastPreview) setPreviewMessageId(lastPreview.id);
  }

  useEffect(() => {
    if (!conversationId) return;
    loadMessages(conversationId);
  }, [conversationId]);

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
        throw new Error(
          (err as { detail?: string }).detail || "Failed to send",
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
                    : m,
                ),
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
              toast.error(
                e instanceof Error ? e.message : "Something went wrong",
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
            } catch (e) {
              console.error(e);
              toast.error(e instanceof Error ? e.message : "Stream error");
              setMessages((prev) =>
                prev.filter((m) => !isStreamingPlaceholder(m.id)),
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
              : m,
          ),
        );
        setStreamingContent("");
      } else {
        console.error(e);
        toast.error(e instanceof Error ? e.message : "Something went wrong");
        setMessages((prev) =>
          prev.filter((m) => !isStreamingPlaceholder(m.id)),
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

  function handleDay0Choice(message: string) {
    if (loading) return;
    send("use", undefined, message);
  }

  function startNewChat() {
    router.replace(buildNewChatUrl(packId));
    resetForNewChat();
  }

  async function handleDeleteConversation(convId: string) {
    try {
      await chatApi.deleteConversation(convId);
      setHistoryList((prev) => prev.filter((c) => c.id !== convId));
      if (conversationId === convId) startNewChat();
    } catch {
      /* e.g. network error or 404 */
    }
  }

  const hasCompletedAssistant = messages.some(
    (m) => m.role === "assistant" && !isStreamingPlaceholder(m.id),
  );

  const hasAnsweredBrandChoice = messages.some(
    (m) =>
      m.role === "user" &&
      (m.content === "Yes, I have a brand" || m.content === "No, new brand"),
  );

  const lastAssistantMessage = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && !isStreamingPlaceholder(m.id));
  const questionContext =
    dayContext && lastAssistantMessage
      ? getQuestionContextFromMessage(lastAssistantMessage)
      : null;

  if (!hasCompletedAssistant) {
    return (
      <div
        ref={containerRef}
        className="flex-1 flex flex-col min-h-0 overflow-y-auto"
      >
        <NextActionBanner nextAction={nextAction} />
        <div className="flex-1 flex flex-col min-h-0 justify-center items-center px-4 py-12">
          <div className="max-w-4xl w-full flex flex-col items-center text-center">
            {messages.length === 0 && !loading && (
              <h2 className="text-4xl  font-[600] text-foreground max-w-lg mx-auto mb-6">
                What are we shipping today?
              </h2>
            )}
            {messages.length > 0 && (
              <div className="w-full max-w-4xl mx-auto flex flex-col items-start text-left mb-6">
                <ChatMessageList
                  messages={messages}
                  streamingContent={streamingContent}
                  loading={loading}
                  onApply={(id) => send("apply", id)}
                />
              </div>
            )}
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
              dayContext={dayContext}
              onDay0Choice={
                dayContext?.day === 0 ? handleDay0Choice : undefined
              }
              showDay0ChoiceChips={!hasAnsweredBrandChoice}
              questionContext={questionContext}
              onQuestionChipClick={(value) => send("use", undefined, value)}
              onResuggest={() =>
                send("use", undefined, "Give me different suggestions")
              }
              onOpenHistory={() => setHistoryModalOpenState(true)}
            />
          </div>
        </div>
        <AnimatePresence>
          <ChatHistoryModal
            open={historyModalOpenState}
            onClose={() => setHistoryModalOpenState(false)}
            conversations={historyList}
            loading={historyLoading}
            packId={packId}
            onDelete={handleDeleteConversation}
          />
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 flex flex-col min-h-0 w-full">
      <NextActionBanner nextAction={nextAction} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-6">
        <div className="w-full max-w-4xl mx-auto flex flex-col items-start text-left">
          <ChatMessageList
            messages={messages}
            streamingContent={streamingContent}
            loading={loading}
            onApply={(id) => send("apply", id)}
          />
        </div>
      </div>
      <div className="shrink-0 px-4 py-4">
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
          dayContext={dayContext}
          onDay0Choice={dayContext?.day === 0 ? handleDay0Choice : undefined}
          showDay0ChoiceChips={!hasAnsweredBrandChoice}
          questionContext={questionContext}
          onQuestionChipClick={(value) => send("use", undefined, value)}
          onResuggest={() =>
            send("use", undefined, "Give me different suggestions")
          }
          onOpenHistory={() => setHistoryModalOpenState(true)}
        />
      </div>
      <ChatFab onNewChat={startNewChat} />
      <AnimatePresence>
        <ChatHistoryModal
          open={historyModalOpenState}
          onClose={() => setHistoryModalOpenState(false)}
          conversations={historyList}
          loading={historyLoading}
          packId={packId}
          onDelete={handleDeleteConversation}
        />
      </AnimatePresence>
    </div>
  );
}
