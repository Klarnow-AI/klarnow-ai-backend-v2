"use client";

import { Film, MessageSquare, Trash2 } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import type { CreativeAsset } from "@/types/api-types";

type VideoAsset = CreativeAsset & { created_at: string };

type AdPreviewPanelProps = {
  videos?: VideoAsset[];
  onDelete?: (assetId: string) => void | Promise<void>;
  onOpenChat?: () => void;
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function AdPreviewPanel({
  videos = [],
  onDelete,
  onOpenChat,
}: AdPreviewPanelProps) {
  if (videos.length === 0) {
    return (
      <div className="relative flex h-full w-full items-center justify-center rounded-2xl border border-border bg-card overflow-hidden">
        <div className="flex flex-col items-center gap-6 px-8 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <Film className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-foreground">No video ads yet</p>
            <p className="max-w-[280px] text-sm leading-relaxed text-muted-foreground">
              Use the chat to generate video ads. They&apos;ll appear here as a
              live preview.
            </p>
          </div>
          {onOpenChat && (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenChat}
              className="gap-2"
            >
              <MessageSquare className="h-4 w-4" />
              Open chat to generate
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-hidden">
      <div className="shrink-0 px-4 py-3 border-b border-border">
        <p className="text-sm text-muted-foreground">
          {videos.length} video ad{videos.length !== 1 ? "s" : ""} — generated via
          chat
        </p>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => (
            <div
              key={video.id}
              className="group flex flex-col rounded-xl border border-border bg-card overflow-hidden"
            >
              <div className="relative flex aspect-video items-center justify-center bg-muted">
                <Film className="h-12 w-12 text-muted-foreground" />
                {onDelete && (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="sm"
                    aria-label="Delete video"
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-background/80 hover:bg-destructive/90"
                    onClick={() => onDelete(video.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </IconButton>
                )}
              </div>
              <div className="p-3 space-y-1">
                {video.script && (
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {video.script}
                  </p>
                )}
                <p className="text-xs text-muted-foreground/70">
                  {formatDate(video.created_at)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
