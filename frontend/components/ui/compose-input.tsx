"use client";

import { forwardRef } from "react";
import {
  Plus,
  Paperclip,
  MessageSquare,
  Feedback,
  Mic,
  Send,
  Stop,
} from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import { cn } from "@/lib/utils";

export interface ComposeInputProps
  extends Omit<
    React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    "value" | "onChange"
  > {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  placeholder: string;
  disabled?: boolean;
  /** When true and onStop is provided, show Stop button instead of Send */
  loading?: boolean;
  onStop?: () => void;
  /** When true, disable the Stop button (chat use) */
  stopTriggered?: boolean;
  /** Optional override for left toolbar (default: Plus, Paperclip, MessageSquare) */
  leftButtons?: React.ReactNode;
  /** Optional override for right icons before submit (default: Feedback, Mic) */
  rightIconsBeforeSubmit?: React.ReactNode;
  wrapperClassName?: string;
}

const ComposeInput = forwardRef<HTMLTextAreaElement, ComposeInputProps>(
  (
    {
      value,
      onChange,
      onSubmit,
      placeholder,
      disabled = false,
      loading = false,
      onStop,
      stopTriggered = false,
      leftButtons,
      rightIconsBeforeSubmit,
      wrapperClassName,
      className,
      ...textareaProps
    },
    ref,
  ) => {
    const showStop = loading && onStop != null;
    const defaultLeft = (
      <>
        <IconButton
          type="button"
          variant="outline"
          size="md"
          aria-label="Add"
          className="border"
        >
          <Plus className="h-4 w-4" />
        </IconButton>
        <IconButton
          type="button"
          variant="outline"
          size="md"
          aria-label="Attach file"
          className="border"
        >
          <Paperclip className="h-4 w-4" />
        </IconButton>
        <IconButton
          type="button"
          variant="outline"
          size="md"
          aria-label="Extensions"
          className="border"
        >
          <MessageSquare className="h-4 w-4" />
        </IconButton>
      </>
    );
    const defaultRightIcons = (
      <>
        <span className="text-muted-foreground" aria-hidden>
          <Feedback className="h-5 w-5" />
        </span>
        <span className="text-muted-foreground" aria-hidden>
          <Mic className="h-5 w-5" />
        </span>
      </>
    );

    return (
      <form onSubmit={onSubmit} className={cn("w-full", wrapperClassName)}>
        <div
          className={cn(
            "relative flex flex-col w-full rounded-xl border border-border bg-card",
            "focus-within:border-foreground/30 focus-within:ring-2 focus-within:ring-ring/30 transition-all",
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              "flex-1 min-w-0 w-full bg-transparent text-foreground placeholder:text-muted-foreground text-base outline-none resize-none min-h-[44px] max-h-[128px] overflow-y-auto leading-relaxed px-4 pt-3 pb-1",
              className,
            )}
            {...textareaProps}
          />
          <div className="flex items-center justify-between gap-2 px-3 pb-2.5 pt-1">
            <div className="flex items-center gap-2 shrink-0">
              {leftButtons ?? defaultLeft}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {rightIconsBeforeSubmit ?? defaultRightIcons}
              {showStop ? (
                <IconButton
                  type="button"
                  variant="solid"
                  size="md"
                  aria-label="Stop"
                  onClick={onStop}
                  disabled={stopTriggered}
                  className="bg-muted text-muted-foreground hover:bg-muted/90 hover:text-foreground"
                >
                  <Stop className="h-4 w-4" />
                </IconButton>
              ) : (
                <IconButton
                  type="submit"
                  variant="solid"
                  size="md"
                  aria-label="Send"
                  disabled={disabled || !value.trim()}
                  className="bg-muted text-muted-foreground hover:bg-muted/90 hover:text-foreground disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                </IconButton>
              )}
            </div>
          </div>
        </div>
      </form>
    );
  },
);
ComposeInput.displayName = "ComposeInput";

export { ComposeInput };
