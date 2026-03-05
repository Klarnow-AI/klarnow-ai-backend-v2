"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { packs as packsApi } from "@/api_requests/packs";
import { PACKS_UPDATED_EVENT_NAME } from "@/contexts/new-pack-modal-context";

export function useHasPacks(): {
  hasPacks: boolean;
  isLoading: boolean;
  error: Error | null;
} {
  const { isAuthenticated } = useAuth();
  const [hasPacks, setHasPacks] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setHasPacks(false);
      setError(null);
      setIsLoading(false);
      setHasLoadedOnce(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await packsApi.list();
      setHasPacks(data.items.length > 0);
    } catch (e) {
      setHasPacks(false);
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
      setHasLoadedOnce(true);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    function onPacksUpdated() {
      void load();
    }
    document.addEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
    return () =>
      document.removeEventListener(PACKS_UPDATED_EVENT_NAME, onPacksUpdated);
  }, [load]);

  return {
    hasPacks,
    // Treat first authenticated fetch as loading to avoid false "no packs" redirects.
    isLoading: isAuthenticated && (!hasLoadedOnce || isLoading),
    error,
  };
}
