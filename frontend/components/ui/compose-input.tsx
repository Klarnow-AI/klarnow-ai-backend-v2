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
  Image,
  Lightbulb,
  Search,
  ShoppingBag,
  MoreVertical,
  ChevronRight,
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
  onAttachFiles?: (files: FileList) => void;
  /** Called when user selects "Create image" */
  onCreateImage?: () => void;
  /** Called when user selects "Thinking" */
  onThinking?: () => void;
  /** Called when user selects "Deep Research" */
  onDeepResearch?: () => void;
  /** Called when user selects "Shopping research" */
  onShoppingResearch?: () => void;
  /** Called when user selects "More" */
  onMore?: () => void;
  /** Optional override for right icons before submit (default: Mic) */
  rightIconsBeforeSubmit?: React.ReactNode;
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
      onOpenHistory,
      voiceRecordingEnabled = true,
      onAttachFiles,
      onCreateImage,
      onThinking,
      onDeepResearch,
      onShoppingResearch,
      onMore,
      wrapperClassName,
      className,
      ...textareaProps
    },
    ref,
  ) => {
    const showStop = loading && onStop != null;
    const valueRef = useRef(value);
    valueRef.current = value;
    const [popoverOpen, setPopoverOpen] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

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
        const files = e.target.files;
        if (files && files.length > 0 && onAttachFiles) {
          onAttachFiles(files);
        }
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

    const handleMenuAction = useCallback((callback?: () => void) => {
      setPopoverOpen(false);
      if (callback) {
        callback();
      } else {
        toast.info("Coming soon");
      }
    }, []);

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
                    className="z-[100] w-56 rounded-xl border border-border bg-card/100 p-2 shadow shadow-black/10"
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
                  <div className="my-2 border-t border-border" />
                  <button
                    type="button"
                    onClick={() => handleMenuAction(onCreateImage)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                  >
                    <Image className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>Create image</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMenuAction(onThinking)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                  >
                    <Lightbulb className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>Thinking</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMenuAction(onDeepResearch)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                  >
                    <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>Deep Research</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMenuAction(onShoppingResearch)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                  >
                    <ShoppingBag className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>Shopping research</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMenuAction(onMore)}
                    className="flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <MoreVertical className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span>More</span>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
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
      <form onSubmit={onSubmit} className={cn("w-full", wrapperClassName)}>
        <div
          className={cn(
            "relative flex flex-col w-full rounded-3xl border border-border bg-card",
            "focus-within:border-foreground/30 transition-all",
            !popoverOpen && "focus-within:scale-[1.02]",
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
              {onOpenHistory && (
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
              )}
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
