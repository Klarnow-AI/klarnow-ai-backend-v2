"use client";

import { useEffect, useState, useCallback, useRef } from "react";

export type UseGetResult<T> = {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
};

/**
 * Fetches data when the key is truthy. Good for GET-style requests that depend on auth or ids.
 *
 * Uses a settledKey pattern so isLoading is derived synchronously — no
 * one-render gap when the key transitions from null to a truthy value.
 */
export function useGet<T>(
  key: string | string[] | null | undefined,
  fetcher: () => Promise<T>
): UseGetResult<T> {
  const keyStr =
    key == null ? "" : Array.isArray(key) ? key.join(":") : String(key);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [settledKey, setSettledKey] = useState(keyStr ? "" : keyStr);

  const prevKeyRef = useRef(keyStr);
  if (prevKeyRef.current !== keyStr) {
    prevKeyRef.current = keyStr;
    setData(null);
    setError(null);
    setSettledKey(keyStr ? "" : keyStr);
  }

  const isLoading = !!keyStr && settledKey !== keyStr;

  const run = useCallback((): (() => void) | undefined => {
    if (!keyStr) return undefined;
    let cancelled = false;
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e : new Error(String(e)));
      })
      .finally(() => {
        if (!cancelled) setSettledKey(keyStr);
      });
    return () => {
      cancelled = true;
    };
  }, [keyStr, fetcher]);

  useEffect(() => {
    const cancel = run();
    return () => {
      cancel?.();
    };
  }, [run]);

  return { data, isLoading, error, refetch: run };
}
