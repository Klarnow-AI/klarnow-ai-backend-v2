"use client";

import { motion } from "framer-motion";
import { Check } from "@/components/icons";
import { AssistantAvatar } from "@/components/assistant-avatar";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/api-types";
import { isStreamingPlaceholder } from "../helpers";

export type ChatMessageItemProps = {
  message: Message;
  streamingContent: string;
  loading: boolean;
  onApply: (messageId: string) => void;
  optionChips?: { label: string; value: string }[];
  onOptionClick?: (value: string) => void;
  showResuggest?: boolean;
  onResuggest?: () => void;
  showMarkDayComplete?: boolean;
  onMarkDayComplete?: () => void;
};

export function ChatMessageItem({
  message,
  streamingContent,
  loading,
  onApply,
  optionChips,
  onOptionClick,
  showResuggest,
  onResuggest,
  showMarkDayComplete,
  onMarkDayComplete,
}: ChatMessageItemProps) {
  const isStreaming = isStreamingPlaceholder(message.id);
  const showOptionChips =
    message.role === "assistant" &&
    optionChips &&
    optionChips.length > 0 &&
    onOptionClick &&
    !isStreaming;
  const showChipRow =
    (showOptionChips || showResuggest || showMarkDayComplete) && !isStreaming;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={cn(
        "flex gap-3 w-full",
        message.role === "user" ? "justify-end" : "justify-start",
      )}
    >
      {message.role === "user" ? (
        <div className="rounded-2xl rounded-tr-md px-4 py-3 max-w-[85%] bg-border/40 text-foreground">
          {message.content && (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          )}
        </div>
      ) : (
        <>
          <AssistantAvatar />
          <div className="rounded-2xl rounded-tl-md px-4 py-3 max-w-[85%] text-sm text-foreground">
            {isStreaming ? (
              <div aria-live="polite" aria-atomic="false">
                <span className="whitespace-pre-wrap">
                  {streamingContent || "\u00A0"}
                </span>
                {loading && (
                  <span
                    className="inline-block w-0.5 h-4 ml-0.5 align-middle bg-current animate-pulse"
                    aria-hidden
                  />
                )}
              </div>
            ) : message.content ? (
              <MarkdownContent>{message.content}</MarkdownContent>
            ) : null}
            {message.is_preview &&
              Array.isArray(message.tool_calls) &&
              message.tool_calls.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    className="gap-1 text-xs"
                    onClick={() => onApply(message.id)}
                    disabled={loading}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Apply
                  </Button>
                </div>
              )}
            {showChipRow && (
              <div className="mt-3 flex flex-wrap gap-2">
                {optionChips?.map((chip) => (
                  <Chip
                    key={chip.value}
                    size="md"
                    onClick={() => onOptionClick?.(chip.value)}
                    disabled={loading}
                    className="cursor-pointer"
                  >
                    {chip.label}
                  </Chip>
                ))}
                {showResuggest && onResuggest && (
                  <Chip
                    size="md"
                    onClick={onResuggest}
                    disabled={loading}
                    className="cursor-pointer opacity-80"
                  >
                    Suggest more options
                  </Chip>
                )}
                {showMarkDayComplete && onMarkDayComplete && (
                  <Chip
                    size="md"
                    icon={<Check className="h-4 w-4" />}
                    onClick={onMarkDayComplete}
                    disabled={loading}
                    className="cursor-pointer"
                  >
                    Mark day complete
                  </Chip>
                )}
              </div>
            )}
          </div>
        </>
      )}
      {message.role === "user" && <div className="w-8 shrink-0" />}
    </motion.div>
  );
}
