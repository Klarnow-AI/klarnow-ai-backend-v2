"use client";

import { Eye, Loader2, Paperclip, X } from "@/components/icons";
import { ComposeInput } from "@/components/ui/compose-input";
import { IconButton } from "@/components/ui/icon-button";
import type { ChatAttachment } from "@/types/api-types";

const UPLOADING_ATTACHMENT_PREFIX = "uploading-";

export type ChatInputBlockProps = {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  loading: boolean;
  stopTriggered: boolean;
  applyTargetId: string | null;
  onOpenHistory?: () => void;
  historyTrigger?: React.ReactNode;
  attachments?: ChatAttachment[];
  onAttachFiles?: (files: File[]) => void;
  onRemoveAttachment?: (attachmentId: string) => void;
};

export function ChatInputBlock({
  input,
  onChange,
  onSubmit,
  onStop,
  loading,
  stopTriggered,
  applyTargetId,
  onOpenHistory,
  historyTrigger,
  attachments = [],
  onAttachFiles,
  onRemoveAttachment,
}: ChatInputBlockProps) {
  return (
    <div className="w-full max-w-[840px] mx-auto flex flex-col items-center text-center">
      {applyTargetId && (
        <div className="mb-2 flex items-center justify-center gap-2 text-sm text-muted-foreground w-full">
          <Eye className="h-4 w-4 shrink-0" />
          <span>
            Reply and click &quot;Apply&quot; to run the proposed changes.
          </span>
        </div>
      )}
      {attachments.length > 0 && (
        <div className="mb-2 w-full flex flex-wrap gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX)
                  ? "border-border/70 bg-muted/20 text-muted-foreground"
                  : "border-border bg-muted/40 text-foreground"
              }`}
            >
              {attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX) ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
              ) : (
                <Paperclip className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              <span className="max-w-[220px] truncate">{attachment.file_name}</span>
              {attachment.id.startsWith(UPLOADING_ATTACHMENT_PREFIX) && (
                <span className="text-[10px] text-muted-foreground">
                  Uploading...
                </span>
              )}
              <IconButton
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Remove ${attachment.file_name}`}
                className="h-5 w-5 rounded-full p-0 text-muted-foreground hover:text-foreground"
                onClick={() => onRemoveAttachment?.(attachment.id)}
              >
                <X className="h-3 w-3" />
              </IconButton>
            </div>
          ))}
        </div>
      )}
      <ComposeInput
        value={input}
        onChange={onChange}
        onSubmit={onSubmit}
        placeholder="Type your message to Klaro…"
        disabled={loading}
        loading={loading}
        onStop={onStop}
        stopTriggered={stopTriggered}
        onOpenHistory={onOpenHistory}
        historyTrigger={historyTrigger}
        onAttachFiles={onAttachFiles}
        allowEmptySubmit={attachments.length > 0}
      />
    </div>
  );
}
