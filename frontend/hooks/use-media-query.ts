"use client";

import { useEffect, useState } from "react";

/**
 * Returns whether the media query matches.
 * On SSR, returns false to avoid hydration mismatch.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** Matches viewport >= 1024px (Tailwind lg) - sidebar visible */
export function useIsSidebarVisible(): boolean {
  return useMediaQuery("(min-width: 1024px)");
}

/** Matches viewport >= 768px (Tailwind md) - pack chat popover vs sheet */
export function useIsTabletOrLarger(): boolean {
  return useMediaQuery("(min-width: 768px)");
}
