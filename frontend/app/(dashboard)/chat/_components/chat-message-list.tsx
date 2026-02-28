"use client";

import { useRef, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import type { DayQuestionContext, Message } from "@/types/api-types";
import { ChatMessageItem } from "./chat-message-item";

export type ChatMessageListProps = {
  messages: Message[];
  streamingContent: string;
  loading: boolean;
  onApply: (messageId: string) => void;
  questionContext?: DayQuestionContext | null;
  lastQuestionMessageId?: string | null;
  onQuestionChipClick?: (value: string) => void;
  onResuggest?: () => void;
  showMarkDayComplete?: boolean;
  onMarkDayComplete?: () => void;
};

export function ChatMessageList({
  messages,
  streamingContent,
  loading,
  onApply,
  questionContext,
  lastQuestionMessageId,
  onQuestionChipClick,
  onResuggest,
  showMarkDayComplete,
  onMarkDayComplete,
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
        {messages.map((m) => {
          const isQuestionMessage =
            m.role === "assistant" &&
            m.id === lastQuestionMessageId &&
            !!questionContext?.suggestion_chips?.length;
          const isLastAssistantMessage =
            m.role === "assistant" && m.id === lastQuestionMessageId;
          return (
            <ChatMessageItem
              key={m.id}
              message={m}
              streamingContent={streamingContent}
              loading={loading}
              onApply={onApply}
              optionChips={
                isQuestionMessage
                  ? questionContext!.suggestion_chips
                  : undefined
              }
              onOptionClick={
                isQuestionMessage ? onQuestionChipClick : undefined
              }
              showResuggest={
                isQuestionMessage && (questionContext?.show_resuggest ?? false)
              }
              onResuggest={onResuggest}
              showMarkDayComplete={
                isLastAssistantMessage && showMarkDayComplete === true
              }
              onMarkDayComplete={onMarkDayComplete}
            />
          );
        })}
      </AnimatePresence>
      <div ref={messagesEndRef} />
    </div>
  );
}
