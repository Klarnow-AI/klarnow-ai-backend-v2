"use client";

import { Film } from "@/components/icons";

export function AdPreviewPanel() {
  return (
    <div className="relative flex h-full w-full items-center justify-center rounded-2xl border border-border bg-card overflow-hidden">
      <div className="flex flex-col items-center gap-4 px-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
          <Film className="h-8 w-8 text-muted-foreground" />
        </div>
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-foreground">
            No ads yet
          </p>
          <p className="max-w-[280px] text-sm leading-relaxed text-muted-foreground">
            Use the chat to generate video ads. They&apos;ll appear here as a
            live preview.
          </p>
        </div>
      </div>
    </div>
  );
}
