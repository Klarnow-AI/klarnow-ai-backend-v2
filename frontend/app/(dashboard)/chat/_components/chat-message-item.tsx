"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Check, Paperclip } from "@/components/icons";
import { AssistantAvatar } from "@/components/assistant-avatar";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { cn } from "@/lib/utils";
import type { StreamStatus } from "@/hooks/use-chat-stream";
import type { Message } from "@/types/api-types";
import { isStreamingPlaceholder } from "../helpers";

const STREAM_STATUS_LABELS: Partial<Record<StreamStatus, string>> = {
  thinking: "Thinking...",
  tool_execution: "Using tools...",
  finalizing: "Finalizing answer...",
};

type ChatActionChip = {
  label: string;
  href: string;
};

type ChatMessageAttachment = {
  id: string;
  file_name: string;
  content_type: string | null;
  size_bytes: number;
  has_text_content: boolean;
};

function isObjectLike(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function extractActionChips(toolResults: unknown): ChatActionChip[] {
  if (!isObjectLike(toolResults)) return [];
  const raw = (toolResults as { actions?: unknown }).actions;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is Record<string, unknown> => isObjectLike(item))
    .map((item) => ({
      label: typeof item.label === "string" ? item.label : "",
      href: typeof item.href === "string" ? item.href : "",
    }))
    .filter((chip) => chip.label.length > 0 && chip.href.length > 0);
}

function extractMessageAttachments(value: unknown): ChatMessageAttachment[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is Record<string, unknown> => isObjectLike(item))
    .map((item) => ({
      id: typeof item.id === "string" ? item.id : "",
      file_name: typeof item.file_name === "string" ? item.file_name : "",
      content_type:
        typeof item.content_type === "string" || item.content_type === null
          ? item.content_type
          : null,
      size_bytes: typeof item.size_bytes === "number" ? item.size_bytes : 0,
      has_text_content: Boolean(item.has_text_content),
    }))
    .filter((item) => item.id.length > 0 && item.file_name.length > 0);
}

export type ChatMessageItemProps = {
  message: Message;
  streamingContent: string;
  streamStatus: StreamStatus;
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
  streamStatus,
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
  const actionChips = extractActionChips(message.tool_results);
  const messageAttachments = extractMessageAttachments(message.attachments);
  const showOptionChips =
    message.role === "assistant" &&
    optionChips &&
    optionChips.length > 0 &&
    onOptionClick &&
    !isStreaming;
  const showChipRow =
    (showOptionChips || showResuggest || showMarkDayComplete) && !isStreaming;
  const streamingStatusLabel = STREAM_STATUS_LABELS[streamStatus];

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
          {messageAttachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {messageAttachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="inline-flex items-center gap-1 rounded-full border border-border/80 bg-background/70 px-2 py-0.5 text-[11px] text-muted-foreground"
                >
                  <Paperclip className="h-3 w-3" />
                  <span className="max-w-[180px] truncate">
                    {attachment.file_name}
                  </span>
                </span>
              ))}
            </div>
          )}
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
                {streamingStatusLabel ? (
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {streamingStatusLabel}
                  </p>
                ) : null}
                {streamingContent ? (
                  <MarkdownContent>{streamingContent}</MarkdownContent>
                ) : (
                  <span className="whitespace-pre-wrap text-muted-foreground">
                    {"\u00A0"}
                  </span>
                )}
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
            {message.role === "assistant" && !isStreaming && actionChips.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {actionChips.map((chip) => (
                  <Link key={`${chip.label}-${chip.href}`} href={chip.href}>
                    <Button size="sm" variant="outline" className="text-xs">
                      {chip.label}
                    </Button>
                  </Link>
                ))}
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
