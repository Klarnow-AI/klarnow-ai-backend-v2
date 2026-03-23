"use client";

import { useEffect, useRef, useState } from "react";
import { Film, MessageSquare, Trash2 } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { IconButton } from "@/components/ui/icon-button";
import type { CreativeAsset } from "@/types/api-types";

type VideoAsset = CreativeAsset & { created_at: string };
const RECENT_PENDING_WINDOW_MS = 10 * 60 * 1000;

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

function isPlayableVideo(video: VideoAsset): boolean {
  return Boolean(video.output_key && video.output_url);
}

function isRecentlyPendingVideo(video: VideoAsset): boolean {
  if (video.output_key) return false;
  const createdAt = Date.parse(video.created_at);
  return Number.isFinite(createdAt) && Date.now() - createdAt < RECENT_PENDING_WINDOW_MS;
}

type VideoPreviewCardProps = {
  video: VideoAsset;
  index: number;
  audioEnabled: boolean;
  onToggleAudio: (videoId: string | null) => void;
  onDelete?: (assetId: string) => void | Promise<void>;
};

function VideoPreviewCard({
  video,
  index,
  audioEnabled,
  onToggleAudio,
  onDelete,
}: VideoPreviewCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playable = isPlayableVideo(video);
  const playbackUrl = video.output_url ?? undefined;

  useEffect(() => {
    const element = videoRef.current;
    if (!element || !playbackUrl) return;
    element.muted = !audioEnabled;
    const playAttempt = element.play();
    if (playAttempt && typeof playAttempt.catch === "function") {
      void playAttempt.catch(() => {});
    }
  }, [audioEnabled, playbackUrl]);

  const handleToggleAudio = () => {
    const element = videoRef.current;
    const nextAudioEnabled = !audioEnabled;
    onToggleAudio(nextAudioEnabled ? video.id : null);
    if (!element) return;
    element.muted = !nextAudioEnabled;
    if (nextAudioEnabled) {
      element.volume = 1;
    }
    const playAttempt = element.play();
    if (playAttempt && typeof playAttempt.catch === "function") {
      void playAttempt.catch(() => {});
    }
  };

  return (
    <div className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card">
      <div className="relative flex aspect-video items-center justify-center bg-muted">
        {playable ? (
          <>
            <video
              ref={videoRef}
              className="h-full w-full bg-black object-cover"
              controls
              autoPlay
              loop
              muted={!audioEnabled}
              playsInline
              preload={index < 2 ? "auto" : "metadata"}
              poster={video.poster_url ?? undefined}
              src={playbackUrl}
            />
            <div className="absolute left-2 top-2 z-10 flex items-center gap-2">
              <button
                type="button"
                onClick={handleToggleAudio}
                className="rounded-md bg-background/85 px-2.5 py-1 text-[11px] font-medium text-foreground shadow-sm backdrop-blur transition-colors hover:bg-background"
              >
                {audioEnabled ? "Mute" : "Sound on"}
              </button>
            </div>
          </>
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 px-4 text-center">
            <Film className="h-12 w-12 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              {isRecentlyPendingVideo(video)
                ? "Preparing playback. This can take a minute."
                : "Playback URL is not available for this video."}
            </p>
          </div>
        )}
        {onDelete && (
          <IconButton
            type="button"
            variant="ghost"
            size="sm"
            aria-label="Delete video"
            className="absolute right-2 top-2 z-10 bg-background/80 transition-colors hover:bg-destructive/90"
            onClick={() => onDelete(video.id)}
          >
            <Trash2 className="h-4 w-4" />
          </IconButton>
        )}
      </div>
      <div className="space-y-1 p-3">
        {video.script && (
          <p className="line-clamp-3 text-xs text-muted-foreground">
            {video.script}
          </p>
        )}
        {playable && playbackUrl && (
          <>
            <p className="text-[11px] text-muted-foreground/70">
              {audioEnabled
                ? "Audio on."
                : "Autoplaying muted. Turn sound on for audio."}
            </p>
            <a
              href={playbackUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex text-xs font-medium text-primary hover:underline"
            >
              Open video
            </a>
          </>
        )}
        <p className="text-xs text-muted-foreground/70">
          {formatDate(video.created_at)}
        </p>
      </div>
    </div>
  );
}

export function AdPreviewPanel({
  videos = [],
  onDelete,
  onOpenChat,
}: AdPreviewPanelProps) {
  const [activeAudioVideoId, setActiveAudioVideoId] = useState<string | null>(null);

  useEffect(() => {
    if (!activeAudioVideoId) return;
    const activeVideoStillPresent = videos.some(
      (video) => video.id === activeAudioVideoId && isPlayableVideo(video),
    );
    if (!activeVideoStillPresent) {
      setActiveAudioVideoId(null);
    }
  }, [activeAudioVideoId, videos]);

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
        <p className="mt-1 text-xs text-muted-foreground/80">
          Preview cards autoplay muted for reliable inline playback. Use Sound
          on for audio.
        </p>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((video, index) => {
            return (
              <VideoPreviewCard
                key={video.id}
                video={video}
                index={index}
                audioEnabled={activeAudioVideoId === video.id}
                onToggleAudio={setActiveAudioVideoId}
                onDelete={onDelete}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
