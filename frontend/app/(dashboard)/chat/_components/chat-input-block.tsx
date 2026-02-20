"use client";

import Link from "next/link";
import { Eye, Paperclip, Send, Stop } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { IconButton } from "@/components/ui/icon-button";
import { SearchInput } from "@/components/ui/search-input";
import type { NextActionChip } from "@/types/api-types";

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
};

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
}: ChatInputBlockProps) {
  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center text-center">
      {applyTargetId && (
        <div className="mb-2 flex items-center justify-center gap-2 text-sm text-muted-foreground w-full">
          <Eye className="h-4 w-4 shrink-0" />
          <span>
            Reply and click &quot;Apply&quot; to run the proposed changes.
          </span>
        </div>
      )}
      <form onSubmit={onSubmit} className="w-full mb-4">
        <SearchInput
          value={input}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Message Klaro…"
          disabled={loading}
          leftAdornment={
            <IconButton
              type="button"
              variant="ghost"
              size="md"
              aria-label="Attach file"
            >
              <Paperclip className="h-4 w-4" />
            </IconButton>
          }
          rightAdornment={
            loading ? (
              <IconButton
                type="button"
                variant="solid"
                size="md"
                aria-label="Stop"
                disabled={stopTriggered}
                onClick={onStop}
              >
                <Stop className="h-4 w-4" />
              </IconButton>
            ) : (
              <IconButton
                type="submit"
                variant="solid"
                size="md"
                aria-label="Send"
                disabled={!input.trim()}
              >
                <Send className="h-4 w-4" />
              </IconButton>
            )
          }
        />
      </form>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Chip
          size="md"
          icon={<Eye className="h-4 w-4" />}
          disabled={loading || !input.trim()}
          onClick={onPreview}
        >
          Preview
        </Chip>
        {suggestionChips?.map((chip) =>
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
        )}
      </div>
    </div>
  );
}
