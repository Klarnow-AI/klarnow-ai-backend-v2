"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Download, Trash2, X } from "@/components/icons";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Dialog } from "@/components/ui/dialog";
import { IconButton } from "@/components/ui/icon-button";
import { patchPosterHtmlForImages } from "@/lib/poster-html";
import { inferPosterCanvasDimensions } from "@/lib/poster-canvas";
import {
  TsxSandboxRenderer,
  type TsxSandboxSnapshot,
} from "./tsx-sandbox-renderer";
import { toast } from "sonner";

declare global {
  interface Window {
    html2canvas?: (
      element: HTMLElement,
      options?: Record<string, unknown>,
    ) => Promise<HTMLCanvasElement>;
  }
}

export type CreativePreviewAsset = {
  id?: string;
  name: string;
  code: string;
};

type CreativePreviewModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: CreativePreviewAsset | null;
  variant: "posters";
  onDelete?: (assetId: string) => void | Promise<void>;
};

function isHtmlAsset(name: string): boolean {
  return name.toLowerCase().endsWith(".html");
}

function isTsxAsset(name: string): boolean {
  const lower = name.toLowerCase();
  return lower.endsWith(".tsx") || lower.endsWith(".jsx");
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

export function CreativePreviewModal({
  open,
  onOpenChange,
  asset,
  onDelete,
}: CreativePreviewModalProps) {
  const posterRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [isDownloading, setIsDownloading] = useState(false);
  const [tsxSnapshot, setTsxSnapshot] = useState<TsxSandboxSnapshot | null>(
    null,
  );
  const [tsxSnapshotError, setTsxSnapshotError] = useState<string | null>(null);
  const isMobile = !useMediaQuery("(min-width: 768px)");

  const canvas = useMemo(() => {
    if (!asset) {
      return { width: 1080, height: 1350, sizeId: null };
    }
    return inferPosterCanvasDimensions(asset.name, asset.code);
  }, [asset]);

  const updateScale = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const width = el.clientWidth - 32;
    const height = el.clientHeight - 48;
    const nextScale = Math.min(1, width / canvas.width, height / canvas.height);
    setScale(Math.max(0.1, nextScale));
  }, [canvas.height, canvas.width]);

  useLayoutEffect(() => {
    updateScale();
    const resizeObserver = new ResizeObserver(updateScale);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    return () => resizeObserver.disconnect();
  }, [open, updateScale]);

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

  useEffect(() => {
    setTsxSnapshot(null);
    setTsxSnapshotError(null);
  }, [asset?.code, asset?.name]);

  const handleDownloadPng = useCallback(async () => {
    if (!asset || isDownloading) return;

    const html2canvas = window.html2canvas;
    if (typeof html2canvas !== "function") {
      toast.error("Download failed", {
        description: "Preview renderer is still loading. Please try again.",
      });
      return;
    }

    const fileName = `${assetLabel(asset.name, "poster")}.png`;
    const isTsx = isTsxAsset(asset.name);

    setIsDownloading(true);
    try {
      if (isTsx) {
        if (!tsxSnapshot) {
          toast.error("Download failed", {
            description:
              tsxSnapshotError ??
              "TSX preview snapshot is not ready yet. Please try again.",
          });
          return;
        }

        const offscreen = document.createElement("div");
        offscreen.style.position = "fixed";
        offscreen.style.left = "-99999px";
        offscreen.style.top = "0";
        offscreen.style.width = `${tsxSnapshot.width}px`;
        offscreen.style.height = `${tsxSnapshot.height}px`;
        offscreen.style.overflow = "hidden";
        offscreen.style.background = "transparent";
        offscreen.style.pointerEvents = "none";
        offscreen.innerHTML = patchPosterHtmlForImages(tsxSnapshot.html);
        document.body.appendChild(offscreen);

        try {
          const canvasEl = await html2canvas(offscreen, {
            scale: 2,
            useCORS: true,
            allowTaint: false,
            backgroundColor: null,
            logging: false,
          });

          canvasEl.toBlob(
            (blob) => {
              if (blob) {
                downloadBlob(blob, fileName);
              }
            },
            "image/png",
            1,
          );
        } finally {
          offscreen.remove();
        }

        return;
      }

      if (!isHtmlAsset(asset.name)) {
        toast.error("Download unavailable", {
          description: "This asset format is not supported for PNG export.",
        });
        return;
      }

      const target = posterRef.current;
      if (!target) return;

      const canvasEl = await html2canvas(target, {
        scale: 2,
        useCORS: true,
        allowTaint: false,
        backgroundColor: null,
        logging: false,
      });

      canvasEl.toBlob(
        (blob) => {
          if (blob) {
            downloadBlob(blob, fileName);
          }
        },
        "image/png",
        1,
      );
    } catch (error) {
      console.error("PNG download failed:", error);
      toast.error("Download failed", {
        description:
          error instanceof Error ? error.message : "Unexpected error",
      });
    } finally {
      setIsDownloading(false);
    }
  }, [asset, isDownloading, tsxSnapshot, tsxSnapshotError]);

  const handleDelete = useCallback(() => {
    if (!asset?.id || !onDelete) return;
    onDelete(asset.id);
    onOpenChange(false);
  }, [asset?.id, onDelete, onOpenChange]);

  if (!asset) return null;

  const isHtml = isHtmlAsset(asset.name);
  const isTsx = isTsxAsset(asset.name);

  const actionButtons = (
    <>
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
      {(isHtml || isTsx) && (
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
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <div
        className="fixed inset-0 z-50 flex flex-col bg-background pt-safe pl-safe pr-safe pb-safe"
        onClick={(event) => event.stopPropagation()}
      >
        {isMobile ? (
          <div className="absolute bottom-20 left-0 right-0 z-10 flex items-center justify-center gap-2 px-4 pb-safe overflow-x-auto">
            {actionButtons}
          </div>
        ) : (
          <div className="absolute right-4 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-3">
            {actionButtons}
          </div>
        )}

        <div
          ref={containerRef}
          className="flex flex-1 items-center justify-center overflow-auto p-4 pt-16 pb-28 min-h-0"
        >
          {isTsx ? (
            <div
              data-poster-content
              className="flex items-start justify-start overflow-hidden origin-center"
              style={{
                width: canvas.width,
                height: canvas.height,
                position: "relative",
                overflow: "hidden",
                flexShrink: 0,
                boxSizing: "border-box",
                transform: `scale(${scale})`,
                transformOrigin: "center center",
              }}
            >
              <TsxSandboxRenderer
                code={asset.code}
                name={asset.name}
                width={canvas.width}
                height={canvas.height}
                onSnapshot={(snapshot, error) => {
                  setTsxSnapshot(snapshot);
                  setTsxSnapshotError(error ?? null);
                }}
              />
            </div>
          ) : isHtml ? (
            <div
              ref={posterRef}
              data-poster-content
              className="flex items-start justify-start overflow-hidden origin-center"
              style={{
                width: canvas.width,
                height: canvas.height,
                position: "relative",
                overflow: "hidden",
                flexShrink: 0,
                boxSizing: "border-box",
                transform: `scale(${scale})`,
                transformOrigin: "center center",
              }}
              dangerouslySetInnerHTML={{
                __html: patchPosterHtmlForImages(asset.code),
              }}
            />
          ) : (
            <div
              className="flex items-center justify-center rounded-lg bg-muted max-w-full max-h-[70vh]"
              style={{
                width: canvas.width,
                height: canvas.height,
                minHeight: 200,
              }}
            >
              <p className="p-4 text-center text-sm text-muted-foreground">
                Unsupported format.
              </p>
            </div>
          )}
        </div>
      </div>
    </Dialog>
  );
}
