"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { chat as chatApi } from "@/api_requests/chat";
import { useMediaQuery } from "@/hooks/use-media-query";
import { useDelayedNextActionToast } from "@/hooks/use-delayed-next-action-toast";
import {
  buildChatUrl,
  buildNewChatUrl,
  dedupeMessagesById,
  isStreamingPlaceholder,
} from "./helpers";
import {
  ChatMessageList,
  ChatInputBlock,
  ChatHistoryModal,
  NextActionBanner,
} from "./_components";
import { me } from "@/api_requests/me";
import type { ChatAttachment, NextAction } from "@/types/api-types";
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
const UPLOADING_ATTACHMENT_PREFIX = "uploading-";

function createUploadingAttachment(
  conversationId: string,
  file: File,
): ChatAttachment {
  const suffix =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    id: `${UPLOADING_ATTACHMENT_PREFIX}${suffix}`,
    conversation_id: conversationId,
    file_name: file.name || "attachment",
    content_type: file.type || null,
    size_bytes: file.size ?? 0,
    has_text_content: false,
    created_at: new Date().toISOString(),
  };
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cFromUrl = searchParams.get("c");
  const packId = searchParams.get("pack") ?? undefined;
  const [historyModalOpenState, setHistoryModalOpenState] = useState(false);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const skipAttachmentClearOnUrlSyncRef = useRef(false);

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
    streamStatus,
    previewMessageId,
    applyTargetId,
    historyList,
    historyLoading,
    stopTriggered,
    setConversationId,
    setMessages,
    setStreamingContent,
    setStreamStatus,
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
      s.streamStatus,
      s.previewMessageId,
      s.applyTargetId,
      s.historyList,
      s.historyLoading,
      s.stopTriggered,
      s.setConversationId,
      s.setMessages,
      s.setStreamingContent,
      s.setStreamStatus,
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
    if (skipAttachmentClearOnUrlSyncRef.current) {
      skipAttachmentClearOnUrlSyncRef.current = false;
      return;
    }
    setAttachments([]);
  }, [cFromUrl, setConversationId, setAttachments]);

  useEffect(() => {
    me.getNextAction(packId ?? null)
      .then(setNextAction)
      .catch(() => setNextAction(null));
  }, [packId]);

  useDelayedNextActionToast({
    nextAction,
    delayMs: 8_000,
    durationMs: 10_000,
  });

  async function ensureConversation() {
    if (conversationId) return conversationId;
    const conv = await chatApi.createConversation(packId);
    setConversationId(conv.id);
    router.replace(buildChatUrl(conv.id, packId));
    return conv.id;
  }

  async function loadMessages(cid: string) {
    const res = await chatApi.getMessages(cid);
    const nextMessages = dedupeMessagesById(res.items);
    setMessages((prev) => {
      if (
        nextMessages.length === 0 &&
        prev.some(
          (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-"),
        )
      )
        return dedupeMessagesById(prev);
      return nextMessages;
    });
    const lastPreview = nextMessages.filter((m) => m.is_preview).pop();
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
    setStreamStatus,
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
      const hasUploadingAttachments = attachments.some((attachment) =>
        attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX),
      );
      if (hasUploadingAttachments) {
        toast.error("Please wait for attachments to finish uploading.");
        return;
      }
      const queuedAttachments = attachments.filter(
        (attachment) =>
          !attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX),
      );
      if (!input.trim() && queuedAttachments.length === 0) return;
      setAttachments([]);
      send("use", undefined, undefined, queuedAttachments);
    }
  }

  function startNewChat() {
    router.replace(buildNewChatUrl(packId));
    setAttachments([]);
    resetForNewChat();
  }

  async function handleAttachFiles(files: File[]) {
    if (loading) return;
    const selectedFiles = files.slice(0, 5);
    if (selectedFiles.length === 0) return;

    const pendingConversationId = conversationId ?? "pending";
    const pendingAttachments = selectedFiles.map((file) =>
      createUploadingAttachment(pendingConversationId, file),
    );
    setAttachments((prev) => [...prev, ...pendingAttachments]);

    if (!conversationId) {
      skipAttachmentClearOnUrlSyncRef.current = true;
    }
    const cid = await ensureConversation();
    if (!cid) {
      skipAttachmentClearOnUrlSyncRef.current = false;
      const pendingIds = new Set(pendingAttachments.map((item) => item.id));
      setAttachments((prev) =>
        prev.filter((attachment) => !pendingIds.has(attachment.id)),
      );
      toast.error("Could not attach file. Please try again.");
      return;
    }

    const pendingByIndex = pendingAttachments.map((attachment) => ({
      ...attachment,
      conversation_id: cid,
    }));
    const pendingIdSet = new Set(pendingByIndex.map((item) => item.id));
    setAttachments((prev) =>
      prev.map((attachment) =>
        pendingIdSet.has(attachment.id)
          ? { ...attachment, conversation_id: cid }
          : attachment,
      ),
    );

    for (let index = 0; index < selectedFiles.length; index += 1) {
      const file = selectedFiles[index];
      const pendingAttachment = pendingByIndex[index];
      try {
        const uploaded = await chatApi.uploadAttachment(cid, file);
        setAttachments((prev) =>
          prev.map((attachment) =>
            attachment.id === pendingAttachment.id ? uploaded : attachment,
          ),
        );
      } catch {
        setAttachments((prev) =>
          prev.filter(
            (attachment) => attachment.id !== pendingAttachment.id,
          ),
        );
        toast.error(`Could not attach ${file.name}`);
      }
    }
  }

  function handleRemoveAttachment(attachmentId: string) {
    setAttachments((prev) =>
      prev.filter((attachment) => attachment.id !== attachmentId),
    );
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
                    attachments={attachments}
                    onAttachFiles={handleAttachFiles}
                    onRemoveAttachment={handleRemoveAttachment}
                    onOpenHistory={() => setHistoryModalOpenState(true)}
                  />
                </div>
              </div>
            ) : (
              <>
                <div className="w-full flex-1 min-h-0 overflow-y-auto mx-auto flex flex-col items-start text-left py-2">
                  <ChatMessageList
                    messages={messages}
                    streamingContent={streamingContent}
                    streamStatus={streamStatus}
                    loading={loading}
                    onApply={(id) => send("apply", id)}
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
                    attachments={attachments}
                    onAttachFiles={handleAttachFiles}
                    onRemoveAttachment={handleRemoveAttachment}
                    onOpenHistory={() => setHistoryModalOpenState(true)}
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
            streamStatus={streamStatus}
            loading={loading}
            onApply={(id) => send("apply", id)}
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
                attachments={attachments}
                onAttachFiles={handleAttachFiles}
                onRemoveAttachment={handleRemoveAttachment}
                onOpenHistory={() => setHistoryModalOpenState(true)}
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
              attachments={attachments}
              onAttachFiles={handleAttachFiles}
              onRemoveAttachment={handleRemoveAttachment}
              onOpenHistory={() => setHistoryModalOpenState(true)}
            />
          )}
          {messages.length === 0 && !loading && (
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt.text}
                  type="button"
                  onClick={() => {
                    const hasUploadingAttachments = attachments.some(
                      (attachment) =>
                        attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX),
                    );
                    if (hasUploadingAttachments) {
                      toast.error(
                        "Please wait for attachments to finish uploading.",
                      );
                      return;
                    }
                    const queuedAttachments = attachments.filter(
                      (attachment) =>
                        !attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX),
                    );
                    setAttachments([]);
                    send("use", undefined, prompt.text, queuedAttachments);
                  }}
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
