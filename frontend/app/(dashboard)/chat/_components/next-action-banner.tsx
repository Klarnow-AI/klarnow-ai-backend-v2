"use client";

import type { NextAction } from "@/types/api-types";
import { ChevronRight } from "@/components/icons";

export function NextActionBanner({ nextAction }: { nextAction: NextAction | null }) {
  if (!nextAction) return null;

  return (
    <div className="shrink-0 px-4 py-2 bg-muted/50 border-b border-border">
      <div className="max-w-4xl mx-auto flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-foreground">Next:</span>
        <span className="text-sm text-muted-foreground">{nextAction.actionText}</span>
        {nextAction.blockerMessage && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            {nextAction.blockerMessage}
          </span>
        )}
        <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
      </div>
    </div>
  );
}
