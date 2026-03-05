"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { patchPosterHtmlForImages } from "@/lib/poster-html";
import { Play } from "@/components/icons";
import { inferPosterCanvasDimensions } from "@/lib/poster-canvas";
import { TsxSandboxRenderer } from "./tsx-sandbox-renderer";

export type CreativeTemplateCardAsset = {
  id?: string;
  name: string;
  code: string;
};

type CreativeTemplateCardProps = {
  asset: CreativeTemplateCardAsset;
  onClick: () => void;
  className?: string;
};

function isHtmlAsset(name: string): boolean {
  return name.toLowerCase().endsWith(".html");
}

function isTsxAsset(name: string): boolean {
  const lower = name.toLowerCase();
  return lower.endsWith(".tsx") || lower.endsWith(".jsx");
}

/** Renders a thumbnail preview of the poster/ad HTML, scaled to fit the container. */
function ThumbnailPreview({ code, name }: { code: string; name: string }) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.2);
  const isHtml = isHtmlAsset(name);
  const isTsx = isTsxAsset(name);
  const canvas = useMemo(
    () => inferPosterCanvasDimensions(name, code),
    [name, code],
  );

  useEffect(() => {
    if ((!isHtml && !isTsx) || !wrapperRef.current) return;
    const el = wrapperRef.current;
    const updateScale = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (w > 0 && h > 0) {
        const s = Math.min(w / canvas.width, h / canvas.height);
        setScale(Math.max(0.1, s));
      }
    };
    updateScale();
    const ro = new ResizeObserver(updateScale);
    ro.observe(el);
    return () => ro.disconnect();
  }, [canvas.height, canvas.width, code, isHtml, isTsx]);

  if (!isHtml && !isTsx) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-muted">
        <span className="text-xs text-muted-foreground">Preview</span>
      </div>
    );
  }

  if (isTsx) {
    return (
      <div
        ref={wrapperRef}
        className="absolute inset-0 overflow-hidden"
        style={{ width: "100%", height: "100%" }}
      >
        <TsxSandboxRenderer
          code={code}
          name={name}
          width={canvas.width}
          height={canvas.height}
          scale={scale}
          className="absolute inset-0"
        />
      </div>
    );
  }

  return (
    <div
      ref={wrapperRef}
      className="absolute inset-0 overflow-hidden"
      style={{ width: "100%", height: "100%" }}
    >
      <div
        data-poster-content
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          width: canvas.width,
          height: canvas.height,
          overflow: "hidden",
          transform: `translate(-50%, -50%) scale(${scale})`,
          transformOrigin: "center center",
        }}
        dangerouslySetInnerHTML={{ __html: patchPosterHtmlForImages(code) }}
      />
    </div>
  );
}

export function CreativeTemplateCard({
  asset,
  onClick,
  className,
}: CreativeTemplateCardProps) {
  const canvas = useMemo(
    () => inferPosterCanvasDimensions(asset.name, asset.code),
    [asset.code, asset.name],
  );

  return (
    <button
      type="button"
      onClick={onClick}
      style={{ aspectRatio: `${canvas.width} / ${canvas.height}` }}
      className={cn(
        "group relative flex w-full min-w-0 overflow-hidden rounded-xl",
        "hover:ring-2 hover:ring-primary/50 hover:shadow-lg transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2",
        className,
      )}
    >
      <div className="relative flex-1 min-h-0 overflow-hidden bg-muted/30">
        <ThumbnailPreview code={asset.code} name={asset.name} />
        <div
          className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"
          aria-hidden
        />
        <div className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/25 shadow-md">
          <Play className="h-4 w-4 text-white ml-0.5" size={16} aria-hidden />
        </div>
      </div>
    </button>
  );
}
