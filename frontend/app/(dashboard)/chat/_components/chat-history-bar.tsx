"use client";

import { Clock } from "@/components/icons";
import { Button } from "@/components/ui/button";

export type ChatHistoryBarProps = {
  onOpenHistory: () => void;
};

export function ChatHistoryBar({ onOpenHistory }: ChatHistoryBarProps) {
  return (
    <div className="shrink-0 flex items-center justify-end px-2 py-2 gap-2 m-4">
      <Button
        type="button"
        variant="secondary"
        size="icon"
        onClick={onOpenHistory}
        className="m-0"
        aria-label="History"
      >
        <Clock className="h-5 w-5" />
      </Button>
    </div>
  );
}
