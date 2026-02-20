"use client";

import { useCallback } from "react";
import { packs as packsApi } from "@/api_requests/packs";
import type { PackGatesResponse } from "@/types/api-types";
import { useGet } from "./use-get";

export function usePackGates(packId: string | undefined | null): {
  gates: PackGatesResponse | null;
  isLoading: boolean;
} {
  const fetcher = useCallback(
    () => packsApi.gates(packId!),
    [packId]
  );
  const { data, isLoading } = useGet<PackGatesResponse>(
    packId ? `pack-gates:${packId}` : null,
    fetcher
  );
  return { gates: data ?? null, isLoading };
}
