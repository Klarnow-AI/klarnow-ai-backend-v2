"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { chat as chatApi } from "@/api_requests/chat";
import { me } from "@/api_requests/me";
import type { Message } from "@/types/api-types";
import type { NextAction } from "@/types/api-types";
import { toast } from "sonner";
import {
  ChatMessageList,
  ChatInputBlock,
} from "@/app/(dashboard)/chat/_components";
import {
  isStreamingPlaceholder,
} from "@/app/(dashboard)/chat/helpers";
import { useChatStream } from "@/hooks/use-chat-stream";

const PENDING_CHAT_KEY = "klarnow-pack-chat-pending";
const EMPTY_STATE_PROMPTS = [
  "Summarize this pack's biggest opportunity.",
  "Give me 3 ad angles for this campaign.",
  "What should I do next to launch faster?",
];

export function PackChatPanel({ packId }: { packId: string }) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

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
  const [previewMessageId, setPreviewMessageId] = useState<string | null>(null);
  const [applyTargetId, setApplyTargetId] = useState<string | null>(null);
  const [stopTriggered, setStopTriggered] = useState(false);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);

  useEffect(() => {
    me.getNextAction(packId)
      .then(setNextAction)
      .catch(() => setNextAction(null));
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
            (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-"),
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
          (m) => isStreamingPlaceholder(m.id) || m.id.startsWith("user-"),
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
              <div className="mt-4 flex flex-wrap justify-center gap-2 max-w-[360px]">
                {EMPTY_STATE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => send("use", undefined, prompt)}
                    className="rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground hover:bg-muted"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
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
