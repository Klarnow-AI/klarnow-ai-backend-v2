"use client";

import { Eye, Target } from "@/components/icons";
import { Chip } from "@/components/ui/chip";
import { ComposeInput } from "@/components/ui/compose-input";
import type { DayQuestionContext } from "@/types/api-types";

export type ChatInputBlockProps = {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  loading: boolean;
  stopTriggered: boolean;
  applyTargetId: string | null;
  dayContext?: { day: number; title: string } | null;
  onDay0Choice?: (message: string) => void;
  showDay0ChoiceChips?: boolean;
  questionContext?: DayQuestionContext | null;
  onQuestionChipClick?: (value: string) => void;
  onResuggest?: () => void;
  onOpenHistory?: () => void;
  onMarkDayComplete?: () => void;
};

const DAY0_CHOICE_YES = "Yes, I have a brand";
const DAY0_CHOICE_NO = "No, new brand";

export function ChatInputBlock({
  input,
  onChange,
  onSubmit,
  onStop,
  loading,
  stopTriggered,
  applyTargetId,
  dayContext,
  onDay0Choice,
  showDay0ChoiceChips = true,
  questionContext,
  onQuestionChipClick,
  onResuggest,
  onOpenHistory,
  onMarkDayComplete,
}: ChatInputBlockProps) {
  const inputPlaceholder = questionContext?.input_placeholder ?? "Type your message to Klaro…";
  return (
    <div className="w-full max-w-[840px] mx-auto flex flex-col items-center text-center">
      {dayContext && (
        <div className="mb-2 flex items-center justify-center gap-2 text-sm text-muted-foreground w-full">
          <Target className="h-4 w-4 shrink-0" />
          <span>
            Day {dayContext.day}: {dayContext.title} — Complete today&apos;s tasks in conversation
          </span>
        </div>
      )}
      {dayContext?.day === 0 && onDay0Choice && showDay0ChoiceChips && (
        <div className="mb-2 flex items-center justify-center gap-2 w-full">
          <Chip
            size="md"
            onClick={() => onDay0Choice(DAY0_CHOICE_YES)}
            disabled={loading}
          >
            {DAY0_CHOICE_YES}
          </Chip>
          <Chip
            size="md"
            onClick={() => onDay0Choice(DAY0_CHOICE_NO)}
            disabled={loading}
          >
            {DAY0_CHOICE_NO}
          </Chip>
        </div>
      )}
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
        placeholder={inputPlaceholder}
        disabled={loading}
        loading={loading}
        onStop={onStop}
        stopTriggered={stopTriggered}
        onOpenHistory={onOpenHistory}
      />
    </div>
  );
}
