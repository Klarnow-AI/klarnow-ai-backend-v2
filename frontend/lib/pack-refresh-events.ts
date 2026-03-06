"use client";

import { useEffect, useRef } from "react";

export const PACK_REFRESH_EVENT_NAME = "pack-refresh";

export type PackRefreshScope =
  | "summary"
  | "today-tasks"
  | "next-action"
  | "gates"
  | "sprint";

export type PackRefreshDetail = {
  packId: string;
  scopes: PackRefreshScope[];
};

export function dispatchPackRefresh(detail: PackRefreshDetail) {
  if (typeof document === "undefined") return;
  document.dispatchEvent(
    new CustomEvent<PackRefreshDetail>(PACK_REFRESH_EVENT_NAME, { detail }),
  );
}

export function usePackRefreshListener(
  packId: string | null | undefined,
  scopes: PackRefreshScope[],
  handler: (detail: PackRefreshDetail) => void,
) {
  const handlerRef = useRef(handler);
  const scopesKey = scopes.join("|");

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!packId || typeof document === "undefined") return;

    const activeScopes = new Set<PackRefreshScope>(scopes);
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<PackRefreshDetail>).detail;
      if (!detail || detail.packId !== packId) return;
      if (!detail.scopes.some((scope) => activeScopes.has(scope))) return;
      handlerRef.current(detail);
    };

    document.addEventListener(PACK_REFRESH_EVENT_NAME, listener);
    return () => {
      document.removeEventListener(PACK_REFRESH_EVENT_NAME, listener);
    };
  }, [packId, scopesKey]);
}
