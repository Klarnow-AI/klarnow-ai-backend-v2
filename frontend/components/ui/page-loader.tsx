"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/** Spinner matching PageLoader style – circular border, optional size via className. */
export function Spinner({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn(
        "rounded-full border-2 border-muted border-t-foreground shrink-0",
        className ?? "h-12 w-12"
      )}
      animate={{ rotate: 360 }}
      transition={{
        duration: 0.8,
        repeat: Infinity,
        ease: "linear",
      }}
      aria-hidden
    />
  );
}

export function PageLoader({
  message,
  variant = "screen",
}: {
  message?: string;
  variant?: "screen" | "overlay";
}) {
  const isOverlay = variant === "overlay";

  return (
    <div
      className={
        isOverlay
          ? "fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/90 backdrop-blur-sm"
          : "min-h-screen flex flex-col items-center justify-center gap-4 bg-background"
      }
      aria-live="polite"
      aria-busy="true"
    >
      <Spinner className="h-12 w-12" />
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
