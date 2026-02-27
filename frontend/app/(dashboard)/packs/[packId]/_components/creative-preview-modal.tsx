"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import {
  ChevronLeft,
  Download,
  Trash2,
  X,
  Heart,
  Share,
  MoreVertical,
} from "@/components/icons";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Dialog } from "@/components/ui/dialog";
import { IconButton } from "@/components/ui/icon-button";
import { CreativeInput } from "./creative-input";

export type CreativePreviewAsset = {
  id?: string;
  name: string;
  code: string;
};

function isHtmlAsset(name: string): boolean {
  return name.toLowerCase().endsWith(".html");
}

function assetLabel(name: string, fallback: string): string {
  return (
    name
      .split("/")
      .pop()
      ?.replace(/\.(tsx|jsx|html)$/, "") ?? fallback
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

type CreativePreviewModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: CreativePreviewAsset | null;
  variant: "posters";
  onDelete?: (assetId: string) => void | Promise<void>;
};

export function CreativePreviewModal({
  open,
  onOpenChange,
  asset,
  variant,
  onDelete,
}: CreativePreviewModalProps) {
  const posterRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [isDownloading, setIsDownloading] = useState(false);
  const [editPrompt, setEditPrompt] = useState("");
  const isMobile = !useMediaQuery("(min-width: 768px)");

  const updateScale = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const w = el.clientWidth - 32;
    const h = el.clientHeight - 48;
    const s = Math.min(1, w / 600, h / 850);
    setScale(Math.max(0.1, s));
  }, []);

  useLayoutEffect(() => {
    updateScale();
    const ro = new ResizeObserver(updateScale);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [updateScale, open]);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.html2canvas === "function"
    ) {
      return;
    }
    const script = document.createElement("script");
    script.src =
      "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
    script.async = true;
    document.head.appendChild(script);
  }, []);

  const handleDownloadPng = useCallback(async () => {
    if (!asset || isDownloading) return;
    if (!isHtmlAsset(asset.name)) return;
    const target = posterRef.current;
    const html2canvas = (
      window as Window & {
        html2canvas?: (
          el: HTMLElement,
          opts?: Record<string, unknown>,
        ) => Promise<HTMLCanvasElement>;
      }
    ).html2canvas;
    if (!target || typeof html2canvas !== "function") return;

    setIsDownloading(true);
    try {
      const canvas = await html2canvas(target, {
        scale: 2,
        useCORS: true,
        allowTaint: false,
        backgroundColor: null,
        logging: false,
      });
      canvas.toBlob(
        (blob) => {
          if (blob) {
            downloadBlob(
              blob,
              `${assetLabel(asset.name, "poster")}.png`,
            );
          }
        },
        "image/png",
        1,
      );
    } catch (e) {
      console.error("PNG download failed:", e);
    } finally {
      setIsDownloading(false);
    }
  }, [asset, isDownloading, variant]);

  const handleDelete = useCallback(() => {
    if (asset?.id && onDelete) {
      onDelete(asset.id);
      onOpenChange(false);
    }
  }, [asset?.id, onDelete, onOpenChange]);

  if (!asset) return null;

  const isHtml = isHtmlAsset(asset.name);

  const actionButtons = (
    <>
      <IconButton
        type="button"
        variant="solid"
        size="lg"
        aria-label="Like"
        className="bg-black/25 text-white hover:opacity-90"
      >
        <Heart className="h-5 w-5" />
      </IconButton>
      <IconButton
        type="button"
        variant="solid"
        size="lg"
        aria-label="Close"
        onClick={() => onOpenChange(false)}
        className="bg-black/25 text-white hover:opacity-90"
      >
        <X className="h-5 w-5" />
      </IconButton>
      {isHtml && (
        <IconButton
          type="button"
          variant="solid"
          size="lg"
          aria-label="Download"
          onClick={handleDownloadPng}
          disabled={isDownloading}
          className="bg-black/25 text-white hover:opacity-90 disabled:opacity-50"
        >
          <Download className="h-5 w-5" />
        </IconButton>
      )}
      <IconButton
        type="button"
        variant="solid"
        size="lg"
        aria-label="Share"
        className="bg-black/25 text-white hover:opacity-90"
      >
        <Share className="h-5 w-5" />
      </IconButton>
      {asset.id && onDelete && (
        <IconButton
          type="button"
          variant="solid"
          size="lg"
          aria-label="Delete"
          onClick={handleDelete}
          className="bg-black/25 text-white hover:opacity-90"
        >
          <Trash2 className="h-5 w-5" />
        </IconButton>
      )}
      <IconButton
        type="button"
        variant="solid"
        size="lg"
        aria-label="More options"
        className="bg-black/25 text-white hover:opacity-90"
      >
        <MoreVertical className="h-5 w-5" />
      </IconButton>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <div
        className="fixed inset-0 z-50 flex flex-col bg-background pt-safe pl-safe pr-safe pb-safe"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top-left: Back button */}
        <div className="absolute left-4 top-4 z-10 pt-safe pl-safe">
          <IconButton
            type="button"
            variant="solid"
            size="lg"
            aria-label="Back"
            onClick={() => onOpenChange(false)}
            className="bg-black/25 text-white hover:opacity-90"
          >
            <ChevronLeft className="h-5 w-5" />
          </IconButton>
        </div>

        {/* Action buttons: right side on desktop, bottom bar on mobile */}
        {isMobile ? (
          <div className="absolute bottom-20 left-0 right-0 z-10 flex items-center justify-center gap-2 px-4 pb-safe overflow-x-auto">
            {actionButtons}
          </div>
        ) : (
          <div className="absolute right-4 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-3">
            {actionButtons}
          </div>
        )}

        {/* Center: Poster content - scales to fit viewport on mobile */}
        <div
          ref={containerRef}
          className="flex flex-1 items-center justify-center overflow-auto p-4 pt-16 pb-28 min-h-0"
        >
          {isHtml ? (
            <div
              ref={posterRef}
              data-poster-content
              className="flex items-center justify-center overflow-hidden origin-center"
              style={{
                width: 600,
                height: 850,
                position: "relative",
                overflow: "hidden",
                flexShrink: 0,
                boxSizing: "border-box",
                transform: `scale(${scale})`,
              }}
              dangerouslySetInnerHTML={{ __html: asset.code }}
            />
          ) : (
            <div
              className="flex items-center justify-center rounded-lg bg-muted max-w-full max-h-[70vh]"
              style={{ width: 600, height: 850, minHeight: 200 }}
            >
              <p className="text-sm text-muted-foreground p-4 text-center">
                Legacy format — full preview in Posters page
              </p>
            </div>
          )}
        </div>

        {/* Bottom: Input bar */}
        <div className="shrink-0 border-t border-border bg-card px-4 py-4 pb-safe">
          <div className="mx-auto max-w-2xl">
            <CreativeInput
              value={editPrompt}
              onChange={setEditPrompt}
              placeholder="Type to edit image..."
            />
          </div>
        </div>
      </div>
    </Dialog>
  );
}
