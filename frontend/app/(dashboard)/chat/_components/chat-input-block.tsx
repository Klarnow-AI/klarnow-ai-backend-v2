"use client";

import Link from "next/link";
import { Check, Eye, Target } from "@/components/icons";
import { Chip } from "@/components/ui/chip";
import { ComposeInput } from "@/components/ui/compose-input";
import type { DayQuestionContext, NextActionChip } from "@/types/api-types";

export type ChatInputBlockProps = {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onPreview: () => void;
  onStop: () => void;
  loading: boolean;
  stopTriggered: boolean;
  applyTargetId: string | null;
  suggestionChips?: NextActionChip[] | null;
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
  onPreview,
  onStop,
  loading,
  stopTriggered,
  applyTargetId,
  suggestionChips,
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
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center text-center">
      {dayContext && (
        <div className="mb-2 flex items-center justify-center gap-2 text-sm text-muted-foreground w-full">
          <Target className="h-4 w-4 shrink-0" />
          <span>
            Day {dayContext.day}: {dayContext.title} — Complete today&apos;s tasks in conversation
          </span>
        </div>
      )}
      {dayContext?.day === 0 && onDay0Choice && showDay0ChoiceChips && (
        <div className="mb-2 flex items-center justify-start gap-2 w-full">
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
        wrapperClassName="mb-4"
      />
      <div className="flex flex-wrap items-center justify-center gap-2">
        {dayContext && dayContext.day >= 0 && dayContext.day <= 3 && onMarkDayComplete && (
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
        <Chip
          size="md"
          icon={<Eye className="h-4 w-4" />}
          disabled={loading || !input.trim()}
          onClick={onPreview}
        >
          Preview
        </Chip>
        {questionContext && onQuestionChipClick ? (
          <>
            {questionContext.suggestion_chips.map((chip) => (
              <Chip
                key={chip.label}
                size="md"
                onClick={() => onQuestionChipClick(chip.value)}
                disabled={loading}
                className="cursor-pointer"
              >
                {chip.label}
              </Chip>
            ))}
            {questionContext.show_resuggest && onResuggest && (
              <Chip
                size="md"
                onClick={onResuggest}
                disabled={loading}
                className="cursor-pointer opacity-80"
              >
                Suggest more options
              </Chip>
            )}
          </>
        ) : (
          suggestionChips?.map((chip) =>
            chip.href ? (
              <Link key={chip.label} href={chip.href}>
                <Chip size="md" className="cursor-pointer">
                  {chip.label}
                </Chip>
              </Link>
            ) : (
              <Chip key={chip.label} size="md">
                {chip.label}
              </Chip>
            )
          )
        )}
      </div>
    </div>
  );
}
