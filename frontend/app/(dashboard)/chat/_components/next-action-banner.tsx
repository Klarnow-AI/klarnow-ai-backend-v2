"use client";

import Link from "next/link";
import type { NextAction } from "@/types/api-types";
import { Target } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function NextActionBanner({
  nextAction,
  center = false,
}: {
  nextAction: NextAction | null;
  center?: boolean;
}) {
  if (!nextAction) return null;

  const primaryChip = nextAction.actionChips.find((c) => c.href);
  const secondaryText = nextAction.blockerMessage ?? nextAction.whyItMatters;
  const isBlocker = !!nextAction.blockerMessage;

  return (
    <div
      className={cn("shrink-0 min-w-0 py-6 mb-6", center && "flex justify-center w-full")}
      style={{ background: "unset", backgroundColor: "unset" }}
    >
      <div
        className={cn(
          "w-full min-w-0 max-w-full rounded-2xl border-0 bg-border/40 px-3 py-3 flex items-center gap-2 sm:gap-4 sm:px-4 overflow-hidden",
          center && "mx-auto max-w-xl",
        )}
      >
        <div className="rounded-full border-0 bg-border/50 p-2 shrink-0">
          <Target className="h-4 w-4 text-muted-foreground" size={16} />
        </div>
        <div className="flex-1 min-w-0 space-y-0.5 overflow-hidden">
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
            <Button
              variant="secondary"
              size="sm"
              className="rounded-full text-xs sm:text-sm whitespace-nowrap px-2.5 sm:px-3"
            >
              {primaryChip.label}
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
