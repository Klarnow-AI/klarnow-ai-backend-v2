"use client";

import Link from "next/link";
import type { NextAction } from "@/types/api-types";
import { Target } from "@/components/icons";
import { Button } from "@/components/ui/button";

export function NextActionBanner({
  nextAction,
}: {
  nextAction: NextAction | null;
}) {
  if (!nextAction) return null;

  const primaryChip = nextAction.actionChips.find((c) => c.href);
  const secondaryText = nextAction.blockerMessage ?? nextAction.whyItMatters;
  const isBlocker = !!nextAction.blockerMessage;

  return (
    <div className="shrink-0 lg:py-10 py-6">
        <div className="max-w-[840px] mx-auto rounded-2xl border border-border bg-card px-4 py-3 flex items-center gap-4">
        <div className="rounded-full border border-border bg-muted/50 p-2 shrink-0">
          <Target className="h-4 w-4 text-muted-foreground" size={16} />
        </div>
        <div className="flex-1 min-w-0 space-y-0.5">
          <p className="text-sm font-medium text-foreground truncate">
            {nextAction.actionText}
          </p>
          {secondaryText && (
            <p
              className={`text-xs truncate ${
                isBlocker
                  ? "text-amber-600 dark:text-amber-400"
                  : "text-muted-foreground"
              }`}
              role={isBlocker ? "alert" : undefined}
            >
              {secondaryText}
            </p>
          )}
        </div>
        {primaryChip && (
          <Link href={primaryChip.href!} className="shrink-0">
            <Button variant="secondary" size="sm" className="rounded-full">
              {primaryChip.label}
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
