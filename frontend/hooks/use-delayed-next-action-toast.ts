"use client";

import { createElement, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { NextAction } from "@/types/api-types";

type UseDelayedNextActionToastOptions = {
  nextAction: NextAction | null;
  enabled?: boolean;
  delayMs?: number;
  durationMs?: number;
};

export function useDelayedNextActionToast({
  nextAction,
  enabled = true,
  delayMs = 8_000,
  durationMs = 10_000,
}: UseDelayedNextActionToastOptions): void {
  const router = useRouter();
  const hasShownRef = useRef(false);
  const hasScheduledRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!enabled || !nextAction) {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      hasScheduledRef.current = false;
      return;
    }

    if (hasShownRef.current || hasScheduledRef.current) return;

    const actionText = nextAction.actionText?.trim();
    if (!actionText) return;

    const secondaryText = nextAction.blockerMessage ?? nextAction.whyItMatters;
    const primaryChip = nextAction.actionChips.find((chip) => !!chip.href);

    hasScheduledRef.current = true;
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      hasShownRef.current = true;

      toast.message("Next action", {
        duration: durationMs,
        className: "next-action-toast",
        description: createElement(
          "div",
          { className: "space-y-1" },
          createElement("p", { className: "text-sm font-medium" }, actionText),
          secondaryText
            ? createElement(
                "p",
                { className: "text-xs text-muted-foreground" },
                secondaryText,
              )
            : null,
        ),
        action:
          primaryChip?.href != null
            ? {
                label: primaryChip.label,
                onClick: () => {
                  const href = primaryChip.href!;
                  if (/^https?:\/\//i.test(href)) {
                    window.location.assign(href);
                    return;
                  }
                  router.push(href);
                },
              }
            : undefined,
      });
    }, delayMs);
  }, [delayMs, durationMs, enabled, nextAction, router]);
}
