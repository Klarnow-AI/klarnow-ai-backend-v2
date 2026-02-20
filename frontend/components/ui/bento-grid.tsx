"use client";

import { cn } from "@/lib/utils";

/**
 * Size variant → CSS Grid span mapping.
 * The grid uses 4 columns × auto rows (each ~160px).
 *
 *   small   = 1 col × 1 row  (standard tile)
 *   medium  = 2 col × 1 row  (wide tile)
 *   large   = 2 col × 2 row  (hero tile)
 *   tall    = 1 col × 2 row  (portrait tile)
 */
export type BentoSize = "small" | "medium" | "large" | "tall";

const SPAN_CLASSES: Record<BentoSize, string> = {
  small: "col-span-1 row-span-1",
  medium: "col-span-2 row-span-1",
  large: "col-span-2 row-span-2",
  tall: "col-span-1 row-span-2",
};

export interface BentoGridProps {
  children: React.ReactNode;
  className?: string;
}

export function BentoGrid({ children, className }: BentoGridProps) {
  return (
    <div
      className={cn(
        "grid w-full",
        "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4",
        "auto-rows-[minmax(160px,1fr)]",
        "gap-3 sm:gap-4",
        "grid-flow-dense",
        className,
      )}
    >
      {children}
    </div>
  );
}

export interface BentoItemProps {
  size?: BentoSize;
  className?: string;
  children: React.ReactNode;
}

export function BentoItem({ size = "small", className, children }: BentoItemProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card overflow-hidden shadow-sm",
        "relative flex",
        SPAN_CLASSES[size],
        className,
      )}
    >
      {children}
    </div>
  );
}
