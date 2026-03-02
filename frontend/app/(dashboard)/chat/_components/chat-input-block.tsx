"use client";

import { Eye } from "@/components/icons";
import { ComposeInput } from "@/components/ui/compose-input";

export type ChatInputBlockProps = {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  loading: boolean;
  stopTriggered: boolean;
  applyTargetId: string | null;
  onOpenHistory?: () => void;
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
      />
    </div>
  );
}
