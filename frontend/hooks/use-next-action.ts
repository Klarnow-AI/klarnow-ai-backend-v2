"use client";

import { useCallback } from "react";
import { me } from "@/api_requests/me";
import type { NextAction } from "@/types/api-types";
import { useGet } from "./use-get";

export function useNextAction(
  enabled: boolean,
  packId?: string | null
): {
  nextAction: NextAction | null;
  isLoading: boolean;
} {
  const key = enabled ? (packId ? `next-action:${packId}` : "next-action") : null;
  const fetcher = useCallback(
    (): Promise<NextAction> => me.getNextAction(packId ?? null),
    [packId]
  );
  const { data, isLoading } = useGet<NextAction>(key, fetcher);
  return { nextAction: data ?? null, isLoading };
}
