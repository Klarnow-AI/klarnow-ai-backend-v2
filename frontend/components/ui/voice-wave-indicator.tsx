"use client";

import { cn } from "@/lib/utils";

const BARS = 5;
const DELAYS = [0, 80, 160, 240, 320];

export function VoiceWaveIndicator({ className }: { className?: string }) {
  return (
    <div
      className={cn("flex items-end gap-0.5", className)}
      role="img"
      aria-label="Listening"
    >
      {Array.from({ length: BARS }).map((_, i) => (
        <span
          key={i}
          className="w-1 min-h-1 h-4 rounded-full bg-current animate-wave-bar origin-bottom"
          style={{ animationDelay: `${DELAYS[i]}ms` }}
        />
      ))}
    </div>
  );
}
