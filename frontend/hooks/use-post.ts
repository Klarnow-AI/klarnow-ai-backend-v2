"use client";

import { useState, useCallback } from "react";

export type UsePostResult<TPayload, TResult> = {
  mutate: (payload: TPayload) => Promise<TResult | undefined>;
  isLoading: boolean;
  error: Error | null;
  resetError: () => void;
};

/**
 * Wraps a mutation (POST/PATCH/DELETE) with loading and error state.
 */
export function usePost<TPayload, TResult>(
  mutationFn: (payload: TPayload) => Promise<TResult>
): UsePostResult<TPayload, TResult> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (payload: TPayload): Promise<TResult | undefined> => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await mutationFn(payload);
        return result;
      } catch (e) {
        const err = e instanceof Error ? e : new Error(String(e));
        setError(err);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [mutationFn]
  );

  const resetError = useCallback(() => setError(null), []);

  return { mutate, isLoading, error, resetError };
}
