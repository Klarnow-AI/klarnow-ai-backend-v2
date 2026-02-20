"use client";

import { useRef, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import type { Message } from "@/types/api-types";
import { ChatMessageItem } from "./chat-message-item";

export type ChatMessageListProps = {
  messages: Message[];
  streamingContent: string;
  loading: boolean;
  onApply: (messageId: string) => void;
};

export function ChatMessageList({
  messages,
  streamingContent,
  loading,
  onApply,
}: ChatMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: loading ? "auto" : "smooth",
    });
  }, [messages, streamingContent, loading]);

  return (
    <div className="w-full space-y-6 pb-4">
      <AnimatePresence>
        {messages.map((m) => (
          <ChatMessageItem
            key={m.id}
            message={m}
            streamingContent={streamingContent}
            loading={loading}
            onApply={onApply}
          />
        ))}
      </AnimatePresence>
      <div ref={messagesEndRef} />
    </div>
  );
}
