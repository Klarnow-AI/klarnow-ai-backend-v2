"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Image, Download, Trash2 } from "@/components/icons";
import { patchPosterHtmlForImages } from "@/lib/poster-html";

// Declare html2canvas loaded from CDN so TypeScript is happy
declare global {
  interface Window {
    html2canvas?: (
      element: HTMLElement,
      options?: Record<string, unknown>,
    ) => Promise<HTMLCanvasElement>;
  }
}

// ─── Legacy iframe renderer (backwards-compat for old .tsx assets) ───────────

const IMPORT_RE = /import\s+[\s\S]*?from\s+['"].*?['"]\s*;?\n?/g;

function stripExports(code: string): string {
  return code
    .replace(IMPORT_RE, "")
    .replace(/export\s+default\s+function\s+/, "function ")
    .replace(/export\s+default\s+class\s+/, "class ")
    .replace(/export\s+default\s+/, "const _default = ")
    .replace(/export\s+function\s+/g, "function ")
    .replace(/export\s+class\s+/g, "class ")
    .replace(/export\s+const\s+/g, "const ")
    .replace(/export\s+let\s+/g, "let ")
    .replace(/export\s+var\s+/g, "var ");
}

function buildLegacySrcDoc(code: string, componentName?: string): string {
  const cleaned = stripExports(code);
  const escaped = cleaned.replace(/<\/script>/gi, "<\\/script>");
  const rootComponent = componentName || "Poster";
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <script src="https://unpkg.com/react@18/umd/react.development.js"><\/script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"><\/script>
  <script src="https://cdn.tailwindcss.com"><\/script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body, #root { height: 100%; }
    body { display: flex; align-items: center; justify-content: center; background: #f5f5f5; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-presets="typescript,react">
    ${escaped}
    try {
      var _Named = typeof ${rootComponent} !== "undefined" ? ${rootComponent} : undefined;
      var _Candidate = (typeof _Named === "function")
        ? _Named
        : (typeof _default !== "undefined" && typeof _default === "function")
          ? _default
          : (typeof App !== "undefined" && typeof App === "function")
            ? App : null;
      var _Root = typeof _Candidate === "function"
        ? _Candidate
        : () => React.createElement("div", { style: { padding: "2rem", color: "#666" } }, "No component found");
      ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(_Root));
    } catch (err) {
      document.getElementById("root").innerHTML =
        '<div style="padding:2rem;color:red;font-size:14px;">Render error: ' + err.message + '</div>';
    }
  <\/script>
  <script>
    window.addEventListener("error", function(e) {
      var root = document.getElementById("root");
      if (root && !root.hasChildNodes()) {
        root.innerHTML = '<div style="padding:2rem;color:red;font-size:14px;">Script error: ' + (e.message || "Unknown error") + '</div>';
      }
    });
  <\/script>
</body>
</html>`;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export type PosterAsset = {
  name: string;
  code: string;
};

type PosterPreviewPanelProps = {
  posters: PosterAsset[];
  isGenerating?: boolean;
  selectedIndex?: number;
  onSelectIndex?: (index: number) => void;
  onDeletePoster?: (index: number) => void;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isHtmlAsset(name: string): boolean {
  return name.toLowerCase().endsWith(".html");
}

function posterLabel(name: string, fallback: string): string {
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

// ─── Component ────────────────────────────────────────────────────────────────

export function PosterPreviewPanel({
  posters,
  isGenerating,
  selectedIndex: controlledIndex,
  onSelectIndex,
  onDeletePoster,
}: PosterPreviewPanelProps) {
  const [internalIndex, setInternalIndex] = useState(0);
  const selectedIndex =
    controlledIndex !== undefined ? controlledIndex : internalIndex;
  const setSelectedIndex = onSelectIndex ?? setInternalIndex;

  // posterRef points directly to the rendered HTML poster div — no iframe
  const posterRef = useRef<HTMLDivElement>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Load html2canvas from CDN once on mount — do NOT install via npm
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

  // When new posters arrive, jump to the latest
  useEffect(() => {
    if (posters.length > 0) {
      setSelectedIndex(posters.length - 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [posters.length]);

  const currentPoster = posters[selectedIndex];

  const handleDownloadPng = useCallback(async () => {
    if (!currentPoster || isDownloading) return;

    if (typeof window.html2canvas !== "function") {
      console.warn("html2canvas is not loaded yet — please try again.");
      return;
    }

    // For HTML assets, capture the poster div directly
    // For legacy TSX assets, we can't easily capture the iframe cross-origin
    if (!isHtmlAsset(currentPoster.name)) {
      console.warn("PNG download is only supported for inline-HTML posters.");
      return;
    }

    const target = posterRef.current;
    if (!target) return;

    setIsDownloading(true);
    try {
      const canvas = await window.html2canvas(target, {
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
              `${posterLabel(currentPoster.name, "poster")}.png`,
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
  }, [currentPoster, isDownloading]);

  // ── Empty state ──────────────────────────────────────────────────────────────

  if (posters.length === 0 && !isGenerating) {
    return (
      <div className="relative flex h-full w-full items-center justify-center rounded-2xl border border-border bg-card overflow-hidden">
        <div className="flex flex-col items-center gap-4 px-8 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <Image className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="space-y-1.5">
            <p className="text-sm font-medium text-foreground">
              No posters yet
            </p>
            <p className="max-w-[280px] text-sm leading-relaxed text-muted-foreground">
              Describe the poster or flyer you&apos;d like to create in the chat
              and it will appear here.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const isHtml = currentPoster ? isHtmlAsset(currentPoster.name) : false;

  // ── Rendered ─────────────────────────────────────────────────────────────────

  return (
    <div className="relative flex flex-col h-full w-full rounded-2xl border border-border bg-card overflow-hidden">
      {/* Tab bar + download button */}
      {posters.length > 0 && (
        <div className="shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-b border-border bg-muted/30 overflow-x-auto">
          <div className="flex items-center gap-2 min-w-0">
            {posters.map((p, i) => (
              <div
                key={`${p.name}-${i}`}
                className={`shrink-0 flex items-center gap-1 rounded-lg overflow-hidden ${
                  i === selectedIndex
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setSelectedIndex(i)}
                  className="rounded-l-lg px-3 py-1.5 text-xs font-medium transition-colors text-left min-w-0"
                >
                  {posterLabel(p.name, `Poster ${i + 1}`)}
                </button>
                {onDeletePoster && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeletePoster(i);
                    }}
                    className="p-1.5 rounded-r-lg transition-transform hover:bg-black/10 hover:scale-105 focus:outline-none focus:scale-105"
                    title="Delete flyer"
                    aria-label="Delete flyer"
                  >
                    <Trash2 className="h-3.5 w-3.5 opacity-80" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="shrink-0">
            {isHtml ? (
              <button
                type="button"
                onClick={handleDownloadPng}
                disabled={isDownloading}
                className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Download as PNG"
              >
                <Download className="h-3.5 w-3.5" />
                {isDownloading ? "Downloading…" : "Download PNG"}
              </button>
            ) : (
              <span className="text-xs text-muted-foreground px-2">
                Legacy asset — download not available
              </span>
            )}
          </div>
        </div>
      )}

      {/* Preview area — scrollable, centers the poster */}
      <div className="flex-1 min-h-0 overflow-auto flex items-start justify-center p-6 bg-muted/20">
        {currentPoster && isHtml ? (
          /*
           * Inline-HTML poster — rendered directly in the page so that
           * html2canvas can capture it without cross-origin or CSS-class issues.
           *
           * The poster canvas MUST use inline styles only (no Tailwind classes)
           * so that html2canvas sees all styles during capture.
           *
           * posterRef is placed on this wrapper; the LLM-generated root div
           * (600×850 with inline styles) lives inside it.
           */
          <div
            ref={posterRef}
            style={{
              width: 600,
              height: 850,
              position: "relative",
              overflow: "hidden",
              flexShrink: 0,
              boxSizing: "border-box",
            }}
            // The generated HTML is a single root div (600×850, inline styles)
            // that fills this container exactly.
            dangerouslySetInnerHTML={{
              __html: patchPosterHtmlForImages(currentPoster.code),
            }}
          />
        ) : currentPoster ? (
          /* Legacy .tsx poster — render inside iframe with React + Tailwind CDN */
          <iframe
            srcDoc={buildLegacySrcDoc(
              currentPoster.code,
              currentPoster.name
                .split("/")
                .pop()
                ?.replace(/\.(tsx|jsx)$/, ""),
            )}
            style={{
              width: 600,
              height: 850,
              border: "none",
              flexShrink: 0,
              display: "block",
            }}
            sandbox="allow-scripts allow-same-origin"
            title={currentPoster.name}
          />
        ) : null}
      </div>

      {/* Generating overlay */}
      {isGenerating && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm rounded-2xl">
          <div className="flex flex-col items-center gap-4">
            <div className="relative h-10 w-10">
              <div className="absolute inset-0 rounded-full border-2 border-muted-foreground/20" />
              <div className="absolute inset-0 rounded-full border-2 border-t-foreground animate-spin" />
            </div>
            <p className="text-sm font-medium text-foreground animate-pulse">
              Generating your poster…
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
