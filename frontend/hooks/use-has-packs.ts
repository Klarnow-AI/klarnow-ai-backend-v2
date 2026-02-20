"use client";

import { useCallback } from "react";
import { useAuth } from "@/contexts/auth-context";
import { packs as packsApi } from "@/api_requests/packs";
import { useGet } from "./use-get";

export function useHasPacks(): {
  hasPacks: boolean;
  isLoading: boolean;
} {
  const { isAuthenticated } = useAuth();
  const fetcher = useCallback(() => packsApi.list(), []);
  const { data, isLoading } = useGet<{ items: unknown[] }>(
    isAuthenticated ? "has-packs" : null,
    fetcher
  );
  return {
    hasPacks: data ? data.items.length > 0 : false,
    isLoading,
  };
}
