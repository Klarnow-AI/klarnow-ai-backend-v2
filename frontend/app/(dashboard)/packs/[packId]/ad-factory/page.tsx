"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { creative as creativeApi } from "@/lib/api";
import { toast } from "sonner";
import { Spinner } from "@/components/ui/page-loader";
import { Button } from "@/components/ui/button";
import { AdPreviewPanel } from "./_components/ad-preview-panel";
import { AdFactoryInputBar } from "./_components/ad-factory-input-bar";
import { usePackLayoutContext } from "../_context/pack-layout-context";
import { useMobileInputNav } from "@/contexts/mobile-input-nav-context";
import { useMediaQuery } from "@/hooks/use-media-query";
import { MobileNavContent } from "@/components/layout/mobile-nav-content";
import { LayoutDashboard, X } from "@/components/icons";
import { IconButton } from "@/components/ui/icon-button";
import type { CreativeAsset } from "@/types/api-types";

const PENDING_CHAT_KEY = "klarnow-pack-chat-pending";

function toVideoAssets(
  items: CreativeAsset[],
): (CreativeAsset & { created_at: string })[] {
  return items
    .filter((a) => a.type === "video")
    .map((a) => ({
      ...a,
      created_at: a.created_at,
    }));
}

export default function AdFactoryPage() {
  const params = useParams();
  const packId = params.packId as string | undefined;
  const packLayout = usePackLayoutContext();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [videos, setVideos] = useState<(CreativeAsset & { created_at: string })[]>([]);

  const refreshVideos = useCallback(async () => {
    if (!packId) return;
    try {
      const res = await creativeApi.listAssets(packId);
      setVideos(toVideoAssets(res.items));
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load video ads",
      );
    } finally {
      setLoading(false);
    }
  }, [packId]);

  useEffect(() => {
    if (!packId) return;
    let cancelled = false;
    (async () => {
      try {
        const assetsRes = await creativeApi.listAssets(packId);
        if (!cancelled) {
          setVideos(toVideoAssets(assetsRes.items));
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load ad factory",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [packId]);

  useEffect(() => {
    if (!packId || typeof document === "undefined") return;
    function onVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      refreshVideos();
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [packId, refreshVideos]);

  const handleDeleteVideo = useCallback(
    async (assetId: string) => {
      if (!packId) return;
      try {
        await creativeApi.deleteAsset(assetId);
        setVideos((prev) => prev.filter((a) => a.id !== assetId));
      } catch {
        toast.error("Could not delete video. Try again.");
      }
    },
    [packId],
  );

  const isMobile = !useMediaQuery("(min-width: 1024px)");
  const { showNavInsteadOfInput, setShowNavInsteadOfInput } =
    useMobileInputNav();

  if (!packId) return null;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-h-0 min-w-0 overflow-hidden">
      <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
        {videos.length === 0 ? (
          <AdPreviewPanel onOpenChat={packLayout?.openChatPopover} />
        ) : (
          <AdPreviewPanel
            videos={videos}
            onDelete={handleDeleteVideo}
            onOpenChat={packLayout?.openChatPopover}
          />
        )}
      </div>

      {/* Bottom bar with input */}
      <div className="shrink-0 px-4 py-4 min-w-0">
        <div className="w-full min-w-0 max-w-2xl mx-auto flex items-center gap-2">
          {isMobile ? (
            <>
              {showNavInsteadOfInput ? (
                <div className="flex-1 min-w-0 min-h-[4.5rem] flex items-center">
                  <MobileNavContent inline className="h-[4.5rem]" />
                </div>
              ) : (
                <div className="flex-1 min-w-0 min-h-[4.5rem] flex items-center">
                  <AdFactoryInputBar
                    packId={packId}
                    onOpenChat={packLayout?.openChatPopover}
                    pendingChatKey={PENDING_CHAT_KEY}
                  />
                </div>
              )}
              <div className="shrink-0">
                {showNavInsteadOfInput ? (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="Back to input"
                    onClick={() => setShowNavInsteadOfInput(false)}
                  >
                    <X className="h-5 w-5" />
                  </IconButton>
                ) : (
                  <IconButton
                    type="button"
                    variant="ghost"
                    size="md"
                    aria-label="Show navigation"
                    onClick={() => setShowNavInsteadOfInput(true)}
                  >
                    <LayoutDashboard className="h-5 w-5" />
                  </IconButton>
                )}
              </div>
            </>
          ) : (
            <AdFactoryInputBar
              packId={packId}
              onOpenChat={packLayout?.openChatPopover}
              pendingChatKey={PENDING_CHAT_KEY}
            />
          )}
        </div>
      </div>
    </div>
  );
}
