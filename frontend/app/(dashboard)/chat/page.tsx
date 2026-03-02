"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { chat as chatApi } from "@/api_requests/chat";
import { useMediaQuery } from "@/hooks/use-media-query";
import {
  buildChatUrl,
  buildNewChatUrl,
  getQuestionContextFromMessage,
  isStreamingPlaceholder,
} from "./helpers";
import { dayGuides } from "@/app/(dashboard)/packs/[packId]/plan-tracker/day/[dayNumber]/_data/dayGuides";
import {
  ChatMessageList,
  ChatInputBlock,
  ChatHistoryModal,
  NextActionBanner,
} from "./_components";
import { packs } from "@/api_requests/packs";
import { me } from "@/api_requests/me";
import type { NextAction } from "@/types/api-types";
import { useChatStore } from "./_store/chat-store";
import { useShallow } from "zustand/react/shallow";
import { toast } from "sonner";
import { useChatStream } from "@/hooks/use-chat-stream";
import { cn } from "@/lib/utils";

const STARTER_PROMPTS = [
  { text: "Give me 3 campaign ideas I can ship this week.", variant: "amber" },
  {
    text: "What's the highest-impact next step for this pack?",
    variant: "emerald",
  },
  { text: "Draft a quick ad angle I can test today.", variant: "violet" },
] as const;

const PROMPT_VARIANT_CLASSES = {
  amber:
    "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300 hover:bg-amber-500/20 hover:border-amber-500/40",
  emerald:
    "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20 hover:border-emerald-500/40",
  violet:
    "border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300 hover:bg-violet-500/20 hover:border-violet-500/40",
} as const;

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
  const [dayReadyToComplete, setDayReadyToComplete] = useState<boolean | null>(
    null,
  );

  useEffect(() => {
    if (packId) {
      try {
        localStorage.setItem("sidebar-last-pack-id", packId);
      } catch {}
    }
  }, [packId]);
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
  const isMobile = !useMediaQuery("(min-width: 1024px)");
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

  useEffect(() => {
    if (!packId || !dayContext || dayContext.day < 0 || dayContext.day > 3) {
      setDayReadyToComplete(null);
      return;
    }
    packs
      .getDayReadiness(packId, dayContext.day)
      .then((res) => setDayReadyToComplete(res.ready))
      .catch(() => setDayReadyToComplete(false));
  }, [packId, dayContext?.day, messages, loading]);

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

  const { send, handleStop } = useChatStream({
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
    onError: (message) => toast.error(message),
  });

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

  function handleMarkDayComplete() {
    if (loading) return;
    send("use", undefined, "Mark this day as complete");
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
      toast.error("Could not delete conversation. Please try again.");
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
  const lastAssistantMessageId = lastAssistantMessage?.id ?? null;
  const questionContext =
    dayContext && lastAssistantMessage
      ? getQuestionContextFromMessage(lastAssistantMessage)
      : null;

  if (!hasCompletedAssistant) {
    return (
      <div ref={containerRef} className="w-full flex flex-col min-h-full">
        <div className="w-full max-w-[840px] mx-auto flex flex-col flex-1 min-h-0 items-center">
          <div className="w-full flex-1 flex flex-col min-h-0">
            {messages.length === 0 && !loading ? (
              <div className="flex-1 flex flex-col items-center justify-center px-4 py-10 text-center">
                <NextActionBanner nextAction={nextAction} center />
                <h3 className="text-2xl sm:text-5xl font-[600] text-foreground mx-auto mb-3">
                  Build your campaign with Klaro
                </h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
                  Start by asking Klaro anything about this pack, get
                  suggestions, update your campaign, or plan your next steps.
                </p>
                <div className="w-full">
                  <ChatInputBlock
                    input={input}
                    onChange={setInput}
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                    loading={loading}
                    stopTriggered={stopTriggered}
                    applyTargetId={applyTargetId}
                    dayContext={dayContext}
                    onDay0Choice={
                      dayContext?.day === 0 ? handleDay0Choice : undefined
                    }
                    showDay0ChoiceChips={!hasAnsweredBrandChoice}
                    questionContext={questionContext}
                    onQuestionChipClick={(value) =>
                      send("use", undefined, value)
                    }
                    onResuggest={() =>
                      send("use", undefined, "Give me different suggestions")
                    }
                    onOpenHistory={() => setHistoryModalOpenState(true)}
                    onMarkDayComplete={
                      dayReadyToComplete ? handleMarkDayComplete : undefined
                    }
                  />
                </div>
              </div>
            ) : (
              <>
                <div className="w-full flex-1 min-h-0 overflow-y-auto mx-auto flex flex-col items-start text-left py-4">
                  <ChatMessageList
                    messages={messages}
                    streamingContent={streamingContent}
                    loading={loading}
                    onApply={(id) => send("apply", id)}
                    questionContext={questionContext}
                    lastQuestionMessageId={lastAssistantMessageId}
                    onQuestionChipClick={(value) =>
                      send("use", undefined, value)
                    }
                    onResuggest={() =>
                      send("use", undefined, "Give me different suggestions")
                    }
                    showMarkDayComplete={dayReadyToComplete ?? false}
                    onMarkDayComplete={
                      dayReadyToComplete ? handleMarkDayComplete : undefined
                    }
                  />
                </div>
                <div className="shrink-0 mt-0 w-full">
                  <ChatInputBlock
                    input={input}
                    onChange={setInput}
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                    loading={loading}
                    stopTriggered={stopTriggered}
                    applyTargetId={applyTargetId}
                    dayContext={dayContext}
                    onDay0Choice={
                      dayContext?.day === 0 ? handleDay0Choice : undefined
                    }
                    showDay0ChoiceChips={!hasAnsweredBrandChoice}
                    questionContext={questionContext}
                    onQuestionChipClick={(value) =>
                      send("use", undefined, value)
                    }
                    onResuggest={() =>
                      send("use", undefined, "Give me different suggestions")
                    }
                    onOpenHistory={() => setHistoryModalOpenState(true)}
                    onMarkDayComplete={
                      dayReadyToComplete ? handleMarkDayComplete : undefined
                    }
                  />
                </div>
              </>
            )}
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
    <div
      ref={containerRef}
      className="w-full flex flex-col min-h-0 flex-1"
    >
      <div className="w-full max-w-[840px] mx-auto flex flex-col items-center flex-1 min-h-0">
        <NextActionBanner nextAction={nextAction} />
        <div className="w-full flex-1 min-h-0 overflow-y-auto flex flex-col items-start text-left">
          <ChatMessageList
            messages={messages}
            streamingContent={streamingContent}
            loading={loading}
            onApply={(id) => send("apply", id)}
            questionContext={questionContext}
            lastQuestionMessageId={lastAssistantMessageId}
            onQuestionChipClick={(value) => send("use", undefined, value)}
            onResuggest={() =>
              send("use", undefined, "Give me different suggestions")
            }
            showMarkDayComplete={dayReadyToComplete ?? false}
            onMarkDayComplete={
              dayReadyToComplete ? handleMarkDayComplete : undefined
            }
          />
        </div>
        <div className="shrink-0 mt-2 w-full">
          {isMobile ? (
            <div className="w-full">
              <ChatInputBlock
                input={input}
                onChange={setInput}
                onSubmit={handleSubmit}
                onStop={handleStop}
                loading={loading}
                stopTriggered={stopTriggered}
                applyTargetId={applyTargetId}
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
                onMarkDayComplete={
                  dayReadyToComplete ? handleMarkDayComplete : undefined
                }
              />
            </div>
          ) : (
            <ChatInputBlock
              input={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              onStop={handleStop}
              loading={loading}
              stopTriggered={stopTriggered}
              applyTargetId={applyTargetId}
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
              onMarkDayComplete={
                dayReadyToComplete ? handleMarkDayComplete : undefined
              }
            />
          )}
          {messages.length === 0 && !loading && (
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt.text}
                  type="button"
                  onClick={() => send("use", undefined, prompt.text)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs transition-colors",
                    PROMPT_VARIANT_CLASSES[prompt.variant],
                  )}
                >
                  {prompt.text}
                </button>
              ))}
            </div>
          )}
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
