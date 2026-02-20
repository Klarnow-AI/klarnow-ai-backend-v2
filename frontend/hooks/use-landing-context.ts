"use client";

import { useCallback } from "react";
import { useAuth } from "@/contexts/auth-context";
import { me } from "@/api_requests/me";
import type { LandingContext } from "@/types/api-types";
import { useGet } from "./use-get";

export function useLandingContext(): {
  context: LandingContext | null;
  isLoading: boolean;
} {
  const { isAuthenticated } = useAuth();
  const fetcher = useCallback(async (): Promise<LandingContext> => {
    const data = await me.landingContext();
    const raw = data as LandingContext & {
      sprint_day?: number | null;
      lead_count?: number | null;
    };
    return {
      pack: raw.pack,
      stage: raw.stage,
      sprintDay: raw.sprintDay ?? raw.sprint_day ?? null,
      leadCount: raw.leadCount ?? raw.lead_count ?? null,
    };
  }, []);
  const { data, isLoading } = useGet<LandingContext>(
    isAuthenticated ? "landing-context" : null,
    fetcher
  );
  return { context: data ?? null, isLoading };
}
