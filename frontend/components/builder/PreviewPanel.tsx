"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Lottie from "lottie-react";
import { useProjectStore } from "@/store/useProjectStore";
import { IconButton } from "@/components/ui/icon-button";
import { RotateCcw } from "@/components/icons";

const IMPORT_RE = /import\s+[\s\S]*?from\s+['"].*?['"]\s*;?\n?/g;
let cachedWebLoadingAnimationData: object | null = null;

async function loadWebLoadingAnimationData(): Promise<object | null> {
  if (cachedWebLoadingAnimationData) {
    return cachedWebLoadingAnimationData;
  }

  try {
    const res = await fetch("/assets/jsons/web-loading.json");
    if (!res.ok) return null;
    const data = await res.json();
    cachedWebLoadingAnimationData = data;
    return data;
  } catch {
    return null;
  }
}

function stripExports(code: string, fallbackName?: string): string {
  return code
    .replace(IMPORT_RE, "")
    .replace(
      /^\s*export\s+\*\s*(?:as\s+\w+\s+)?from\s+['"][^'"]*['"]\s*;?\s*$/gm,
      "",
    )
    .replace(
      /^\s*export\s+type\s+\{[^}]*\}\s*(?:from\s+['"][^'"]*['"]\s*)?;?\s*$/gm,
      "",
    )
    .replace(/^\s*export\s+interface\s+/gm, "interface ")
    .replace(/^\s*export\s+type\s+(\w)/gm, "type $1")
    .replace(/^\s*export\s+enum\s+/gm, "enum ")
    .replace(/export\s+default\s+function\s+/, "function ")
    .replace(/export\s+default\s+class\s+/, "class ")
    .replace(
      /export\s+default\s+/,
      fallbackName ? `const ${fallbackName} = ` : "const _default = ",
    )
    .replace(/export\s+function\s+/g, "function ")
    .replace(/export\s+class\s+/g, "class ")
    .replace(/export\s+const\s+/g, "const ")
    .replace(/export\s+let\s+/g, "let ")
    .replace(/export\s+var\s+/g, "var ")
    .replace(
      /^\s*export\s+\{[^}]*\}\s*(?:from\s+['"][^'"]*['"]\s*)?;?\s*$/gm,
      "",
    );
}

/**
 * Produces a single JS bundle from the project files by stripping imports
 * and concatenating component code. This is sent to the persistent iframe
 * via postMessage; it is NOT embedded in HTML, so </script> escaping is
 * not needed here.
 */
function buildBundle(files: Record<string, string>): string {
  const appCode = files["/App.tsx"] || files["App.tsx"] || "";

  let bundle = "";
  Object.entries(files).forEach(([path, code]) => {
    if (path === "/App.tsx" || path === "App.tsx") return;
    const name = path
      .split("/")
      .pop()
      ?.replace(/\.(tsx|jsx)$/, "");
    if (!name) return;
    bundle += stripExports(code, name) + "\n\n";
  });
  bundle += stripExports(appCode);

  return bundle;
}

type Viewport = "mobile" | "tablet" | "desktop";

const VIEWPORT_CONFIG: Record<Viewport, { label: string; width: string }> = {
  mobile: { label: "Mobile (375px)", width: "375px" },
  tablet: { label: "Tablet (768px)", width: "768px" },
  desktop: { label: "Desktop", width: "100%" },
};

function SmartphoneIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="7" y="2" width="10" height="20" rx="2" />
      <circle cx="12" cy="18.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TabletIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <circle cx="12" cy="18.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function MonitorIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8M12 17v4" />
    </svg>
  );
}

const VIEWPORT_ICONS: Record<
  Viewport,
  (props: { className?: string }) => React.ReactElement
> = {
  mobile: SmartphoneIcon,
  tablet: TabletIcon,
  desktop: MonitorIcon,
};

type PreviewPanelProps = {
  /** Optional callback to register a refresh function for external use (e.g. browser chrome). */
  onRegisterRefresh?: (refresh: () => void) => void;
};

export function PreviewPanel({ onRegisterRefresh }: PreviewPanelProps = {}) {
  const files = useProjectStore((s) => s.files);
  const isGenerating = useProjectStore((s) => s.isGenerating);
  const [viewport, setViewport] = useState<Viewport>("desktop");
  const [loadingAnimationData, setLoadingAnimationData] = useState<
    object | null
  >(null);
  const [loadingAnimationFailed, setLoadingAnimationFailed] = useState(false);

  const iframeRef = useRef<HTMLIFrameElement>(null);
  // Tracks whether the iframe has finished its initial load (CDN scripts ready)
  const isLoadedRef = useRef(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sendBundle = useCallback((bundle: string) => {
    iframeRef.current?.contentWindow?.postMessage(
      { type: "UPDATE", code: bundle },
      "*",
    );
  }, []);

  // Called once when the iframe finishes loading (all CDN scripts are ready)
  const handleLoad = useCallback(() => {
    isLoadedRef.current = true;
    // Read latest files directly from store to avoid stale closure
    sendBundle(buildBundle(useProjectStore.getState().files));
  }, [sendBundle]);

  // On subsequent file changes, debounce and send the new bundle
  useEffect(() => {
    if (!isLoadedRef.current) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      sendBundle(buildBundle(files));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [files, sendBundle]);

  // Register refresh with parent for external triggers (e.g. mobile browser chrome)
  useEffect(() => {
    if (!onRegisterRefresh) return;
    onRegisterRefresh(() => sendBundle(buildBundle(files)));
  }, [onRegisterRefresh, sendBundle, files]);

  useEffect(() => {
    let cancelled = false;

    loadWebLoadingAnimationData()
      .then((data) => {
        if (cancelled) return;
        setLoadingAnimationData(data);
        setLoadingAnimationFailed(!data);
      })
      .catch(() => {
        if (!cancelled) setLoadingAnimationFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col w-full h-full overflow-hidden">
      {/* Viewport toolbar */}
      <div className="shrink-0 flex items-center justify-center gap-1 px-3 py-1.5 border-b border-border bg-card">
        {(["mobile", "tablet", "desktop"] as Viewport[]).map((v) => {
          const Icon = VIEWPORT_ICONS[v];
          return (
            <button
              key={v}
              onClick={() => setViewport(v)}
              title={VIEWPORT_CONFIG[v].label}
              className={`p-1.5 rounded-md transition-colors ${
                viewport === v
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
              }`}
            >
              <Icon className="w-4 h-4" />
            </button>
          );
        })}
      </div>

      {/* Preview area */}
      <div className="relative flex-1 min-h-0 overflow-auto bg-muted/30">
        <IconButton
          variant="outline"
          size="sm"
          aria-label="Refresh preview"
          onClick={() => sendBundle(buildBundle(files))}
          className="absolute top-2 right-2 z-20"
        >
          <RotateCcw className="h-4 w-4" />
        </IconButton>

        <div
          className="h-full transition-[width] duration-200"
          style={{
            width: VIEWPORT_CONFIG[viewport].width,
            maxWidth: "100%",
            margin: "0 auto",
          }}
        >
          <iframe
            ref={iframeRef}
            src="/preview-frame.html"
            onLoad={handleLoad}
            className="block w-full h-full border-0 bg-white"
            sandbox="allow-scripts"
            title="Website Preview"
          />
        </div>

        {isGenerating && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-4">
              {loadingAnimationFailed || !loadingAnimationData ? (
                <div className="relative h-10 w-10">
                  <div className="absolute inset-0 rounded-full border-2 border-muted-foreground/20" />
                  <div className="absolute inset-0 rounded-full border-2 border-t-foreground animate-spin" />
                </div>
              ) : (
                <Lottie
                  animationData={loadingAnimationData}
                  loop
                  autoplay
                  className="h-120 w-120"
                />
              )}
              <p className="text-sm font-medium text-foreground animate-pulse">
                Building your page...
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
