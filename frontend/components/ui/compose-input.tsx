"use client";

import { forwardRef, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Plus,
  Paperclip,
  Mic,
  Send,
  Stop,
  Clock,
} from "@/components/icons";
import { useVoiceRecorder } from "@/hooks/use-voice-recorder";
import { useDynamicPopover } from "@/hooks/use-dynamic-popover";
import { IconButton } from "@/components/ui/icon-button";
import { VoiceWaveIndicator } from "@/components/ui/voice-wave-indicator";
import { cn } from "@/lib/utils";

export interface ComposeInputProps extends Omit<
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
  /** Optional override for left toolbar (default: Plus opens popover) */
  leftButtons?: React.ReactNode;
  /** Called when user attaches files via the popover */
  onAttachFiles?: (files: File[]) => void;
  /** Optional override for right icons before submit (default: Mic) */
  rightIconsBeforeSubmit?: React.ReactNode;
  /** When true, submit button can be enabled without text input. */
  allowEmptySubmit?: boolean;
  /** Optional override for history trigger (default: Clock button) */
  historyTrigger?: React.ReactNode;
  /** When provided, renders a History button (Clock icon) before the mic */
  onOpenHistory?: () => void;
  /** When false, Mic is non-interactive (default: true) */
  voiceRecordingEnabled?: boolean;
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
      allowEmptySubmit = false,
      historyTrigger,
      onOpenHistory,
      voiceRecordingEnabled = true,
      onAttachFiles,
      wrapperClassName,
      className,
      onKeyDown: textareaOnKeyDown,
      ...textareaProps
    },
    ref,
  ) => {
    const showStop = loading && onStop != null;
    const valueRef = useRef(value);
    valueRef.current = value;
    const formRef = useRef<HTMLFormElement>(null);
    const [popoverOpen, setPopoverOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          formRef.current?.requestSubmit();
          return;
        }
        textareaOnKeyDown?.(e);
      },
      [textareaOnKeyDown],
    );

    const { refs, floatingStyles, isPositioned } = useDynamicPopover({
      open: popoverOpen,
      placement: "top-start",
      offset: 12,
    });

    useEffect(() => {
      function handler(e: MouseEvent) {
        const target = e.target as Node;
        const ref = refs.reference.current;
        if (
          (ref instanceof Element && ref.contains(target)) ||
          refs.floating.current?.contains(target)
        )
          return;
        setPopoverOpen(false);
      }
      if (popoverOpen) {
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
      }
    }, [popoverOpen, refs.reference, refs.floating]);

    const handleAttachClick = useCallback(() => {
      setPopoverOpen(false);
      fileInputRef.current?.click();
    }, []);

    const handleFileChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files ?? []);
        if (selectedFiles.length === 0 || !onAttachFiles) {
          e.target.value = "";
          return;
        }
        onAttachFiles(selectedFiles);
        e.target.value = "";
      },
      [onAttachFiles],
    );

    const handleTranscription = useCallback(
      (transcript: string) => {
        const current = valueRef.current;
        onChange(current ? `${current} ${transcript}` : transcript);
      },
      [onChange],
    );

    const { isRecording, toggle, supported } = useVoiceRecorder({
      onTranscription: handleTranscription,
      onError: (msg) => toast.error(msg),
    });

    const micDisabled =
      disabled || loading || !supported || !voiceRecordingEnabled;

    const defaultLeft = (
      <div ref={refs.setReference} className="relative shrink-0">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*,.pdf,.doc,.docx"
          className="hidden"
          onChange={handleFileChange}
        />
        <IconButton
          type="button"
          variant="outline"
          size="md"
          aria-label="Add"
          aria-expanded={popoverOpen}
          className="border"
          onClick={() => setPopoverOpen((o) => !o)}
        >
          <Plus className="h-4 w-4" />
        </IconButton>
        {typeof document !== "undefined" &&
          createPortal(
            <AnimatePresence>
              {popoverOpen && (
                <div
                  ref={refs.setFloating}
                  style={{
                    ...floatingStyles,
                    visibility: isPositioned ? "visible" : "hidden",
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: isPositioned ? 1 : 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="z-[100] w-56 rounded-xl border-0 bg-border/80 backdrop-blur-xl p-2 shadow shadow-black/10"
                  >
                    <button
                      type="button"
                      onClick={handleAttachClick}
                      className="flex w-full min-w-0 items-center gap-2 overflow-hidden rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                    >
                      <Paperclip className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 truncate">
                        Attach photo, video, docx
                      </span>
                    </button>
                  </motion.div>
                </div>
              )}
            </AnimatePresence>,
            document.body,
          )}
      </div>
    );
    const defaultRightIcons = isRecording ? (
      <div className="flex items-center gap-1.5">
        <VoiceWaveIndicator className="h-4 text-destructive" />
        <IconButton
          type="button"
          variant="ghost"
          size="md"
          aria-label="Stop voice input"
          onClick={toggle}
          title="Stop recording"
          className="text-destructive"
        >
          <Stop className="h-5 w-5" />
        </IconButton>
      </div>
    ) : (
      <IconButton
        type="button"
        variant="ghost"
        size="md"
        aria-label="Start voice input"
        onClick={toggle}
        disabled={micDisabled}
        title={
          !supported ? "Voice input not supported in this browser" : undefined
        }
        className="text-muted-foreground"
      >
        <Mic className="h-5 w-5" />
      </IconButton>
    );

    return (
      <form
        ref={formRef}
        onSubmit={onSubmit}
        className={cn("w-full", wrapperClassName)}
      >
        <div
          className={cn(
            "relative flex flex-col w-full rounded-3xl border-0 bg-border/40",
            "focus-within:bg-border/60 focus-within:ring-1 focus-within:ring-foreground/20 transition-all",
            !popoverOpen && "focus-within:scale-[1.02]",
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={cn(
              "flex-1 min-w-0 w-full bg-transparent text-foreground placeholder:text-muted-foreground text-base outline-none resize-none min-h-[56px] max-h-[200px] overflow-y-auto leading-relaxed px-4 pt-3 pb-1",
              className,
            )}
            {...textareaProps}
          />
          <div className="flex items-center justify-between gap-2 px-3 pb-2.5 pt-1">
            <div className="flex items-center gap-2 shrink-0">
              {leftButtons ?? defaultLeft}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {historyTrigger ??
                (onOpenHistory && (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="History"
                    onClick={onOpenHistory}
                    disabled={disabled || loading}
                    className="text-muted-foreground"
                  >
                    <Clock className="h-5 w-5" />
                  </IconButton>
                ))}
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
                  disabled={disabled || (!value.trim() && !allowEmptySubmit)}
                  className="disabled:opacity-50"
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
