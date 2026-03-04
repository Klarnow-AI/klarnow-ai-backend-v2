"use client";

import { useCallback, useEffect, useState } from "react";
import { chat as chatApi } from "@/api_requests/chat";
import { Clock, Pencil } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import type { Message, Conversation, ChatAttachment } from "@/types/api-types";
import { toast } from "sonner";
import {
  ChatMessageList,
  ChatInputBlock,
} from "@/app/(dashboard)/chat/_components";
import {
  dedupeMessagesById,
  isStreamingPlaceholder,
} from "@/app/(dashboard)/chat/helpers";
import { useChatStream } from "@/hooks/use-chat-stream";
import type { StreamStatus } from "@/hooks/use-chat-stream";
import { PackChatHistoryDropdown } from "./pack-chat-history-dropdown";

const PENDING_CHAT_KEY = "klarnow-pack-chat-pending";
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

export function PackChatPanel({ packId }: { packId: string }) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([]);

  useEffect(() => {
    if (!packId || typeof window === "undefined") return;
    try {
      const key = `${PENDING_CHAT_KEY}-${packId}`;
      const pending = sessionStorage.getItem(key);
      if (pending) {
        sessionStorage.removeItem(key);
        setInput(pending);
      }
    } catch {
      /* ignore */
    }
  }, [packId]);
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [streamStatus, setStreamStatus] = useState<StreamStatus>("idle");
  const [previewMessageId, setPreviewMessageId] = useState<string | null>(null);
  const [applyTargetId, setApplyTargetId] = useState<string | null>(null);
  const [stopTriggered, setStopTriggered] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [composerHistoryOpen, setComposerHistoryOpen] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [historyList, setHistoryList] = useState<Conversation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const refreshSuggestedPrompts = useCallback(async (reset = false) => {
    if (!packId) return;
    if (reset) setSuggestedPrompts([]);
    try {
      const res = await chatApi.getSuggestedPrompts(packId);
      setSuggestedPrompts(Array.isArray(res.prompts) ? res.prompts.slice(0, 3) : []);
    } catch {
      setSuggestedPrompts([]);
    }
  }, [packId]);

  useEffect(() => {
    void refreshSuggestedPrompts(true);
  }, [refreshSuggestedPrompts]);

  useEffect(() => {
    if (!historyOpen && !composerHistoryOpen) return;
    setHistoryLoading(true);
    chatApi
      .listConversations(packId)
      .then((res) => setHistoryList(res.items))
      .catch(() => setHistoryList([]))
      .finally(() => setHistoryLoading(false));
  }, [historyOpen, composerHistoryOpen, packId]);

  useEffect(() => {
    if (historyOpen || composerHistoryOpen) return;
    setHistorySearch("");
  }, [historyOpen, composerHistoryOpen]);

  useEffect(() => {
    if (!packId) return;
    chatApi
      .listConversations(packId)
      .then((res) => {
        if (res.items.length === 0) return;
        const latest = res.items[0];
        setConversationId((current) => current ?? latest.id);
      })
      .catch(() => {
        /* keep current local state */
      });
  }, [packId]);

  useEffect(() => {
    if (!conversationId) return;
    chatApi.getMessages(conversationId).then((res) => {
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
    if (lastPreview) {
      setPreviewMessageId(lastPreview.id);
      setApplyTargetId(lastPreview.id);
    }
  }

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

  async function handleAttachFiles(files: File[]) {
    if (loading) return;
    const selectedFiles = files.slice(0, 5);
    if (selectedFiles.length === 0) return;

    const pendingConversationId = conversationId ?? "pending";
    const pendingAttachments = selectedFiles.map((file) =>
      createUploadingAttachment(pendingConversationId, file),
    );
    setAttachments((prev) => [...prev, ...pendingAttachments]);

    const cid = await ensureConversation();
    if (!cid) {
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

  function startNewChat() {
    setHistoryOpen(false);
    setComposerHistoryOpen(false);
    setConversationId(null);
    setMessages([]);
    setStreamingContent("");
    setStreamStatus("idle");
    setPreviewMessageId(null);
    setApplyTargetId(null);
    setAttachments([]);
    void refreshSuggestedPrompts();
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 rounded-2xl border border-border bg-card overflow-hidden">
      <div className="shrink-0 px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Chat with Klaro
        </h2>
        <div className="flex items-center gap-2">
          <PackChatHistoryDropdown
            open={historyOpen}
            onOpenChange={(open) => {
              setHistoryOpen(open);
              if (open) setComposerHistoryOpen(false);
            }}
            conversations={historyList}
            loading={historyLoading}
            activeConversationId={conversationId}
            searchQuery={historySearch}
            onSearchQueryChange={setHistorySearch}
            onSelectConversation={(convId) => {
              setAttachments([]);
              setConversationId(convId);
            }}
          />
          <IconButton
            type="button"
            variant="ghost"
            size="sm"
            aria-label="New chat"
            onClick={startNewChat}
          >
            <Pencil className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="flex-1 min-h-0 overflow-y-auto px-2 py-2 flex flex-col">
          {messages.length === 0 && !loading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center px-4 py-8 min-h-[140px]">
              <p className="text-sm font-medium text-foreground mb-1.5">
                Start a conversation
              </p>
              <p className="text-sm text-muted-foreground max-w-[280px] leading-relaxed">
                Ask Klaro anything about this pack, get suggestions, update your
                campaign, or plan your next steps.
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Tip: attach up to 3 images for visual context in your prompt.
              </p>
              {suggestedPrompts.length > 0 ? (
                <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-[360px]">
                  {suggestedPrompts.map((prompt) => (
                    <button
                      key={prompt}
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
                        send("use", undefined, prompt, queuedAttachments);
                      }}
                      className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground hover:bg-muted"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <ChatMessageList
              messages={messages}
              streamingContent={streamingContent}
              streamStatus={streamStatus}
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
            onStop={handleStop}
            loading={loading}
            stopTriggered={stopTriggered}
            applyTargetId={applyTargetId}
            attachments={attachments}
            onAttachFiles={handleAttachFiles}
            onRemoveAttachment={handleRemoveAttachment}
            historyTrigger={
              <PackChatHistoryDropdown
                open={composerHistoryOpen}
                onOpenChange={(open) => {
                  setComposerHistoryOpen(open);
                  if (open) setHistoryOpen(false);
                }}
                conversations={historyList}
                loading={historyLoading}
                activeConversationId={conversationId}
                searchQuery={historySearch}
                onSearchQueryChange={setHistorySearch}
                onSelectConversation={(convId) => {
                  setAttachments([]);
                  setConversationId(convId);
                }}
                trigger={
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="Open chat history"
                    disabled={loading}
                    className="text-muted-foreground"
                  >
                    <Clock className="h-5 w-5" />
                  </IconButton>
                }
              />
            }
          />
        </div>
      </div>
    </div>
  );
}
