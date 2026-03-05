"use client";

import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

const IMPORT_RE = /^\s*import\s+[\s\S]*?;\s*$/gm;

function stripModuleSyntax(code: string): string {
  return code
    .replace(IMPORT_RE, "")
    .replace(/export\s+default\s+function\s+([A-Za-z_$][\w$]*)\s*\(/g, "function $1(")
    .replace(/export\s+default\s+function\s*\(/g, "function __DefaultComponent(")
    .replace(/export\s+default\s+class\s+([A-Za-z_$][\w$]*)/g, "class $1")
    .replace(/export\s+default\s+class\s*/g, "class __DefaultComponent ")
    .replace(/export\s+default\s+([A-Za-z_$][\w$]*)\s*;?/g, "const __DefaultExport = $1;")
    .replace(/export\s+const\s+/g, "const ")
    .replace(/export\s+let\s+/g, "let ")
    .replace(/export\s+var\s+/g, "var ")
    .replace(/export\s+function\s+/g, "function ")
    .replace(/export\s+class\s+/g, "class ");
}

function extractDefaultExportFunctionName(code: string): string | null {
  const match = code.match(/export\s+default\s+function\s+([A-Za-z_$][\w$]*)\s*\(/);
  return match?.[1] ?? null;
}

function escapeForScript(code: string): string {
  return code.replace(/<\/script>/gi, "<\\/script>");
}

export type TsxSandboxSnapshot = {
  html: string;
  width: number;
  height: number;
};

type TsxSandboxRendererProps = {
  code: string;
  name: string;
  width: number;
  height: number;
  scale?: number;
  className?: string;
  onSnapshot?: (snapshot: TsxSandboxSnapshot | null, error?: string) => void;
};

export function TsxSandboxRenderer({
  code,
  name,
  width,
  height,
  scale = 1,
  className,
  onSnapshot,
}: TsxSandboxRendererProps) {
  const [frameId] = useState(
    () => `tsx-sandbox-${Math.random().toString(36).slice(2, 10)}`,
  );

  useEffect(() => {
    if (!onSnapshot) return;

    const onMessage = (event: MessageEvent) => {
      const payload = event.data as
        | {
            type?: string;
            frameId?: string;
            html?: string;
            width?: number;
            height?: number;
            error?: string;
          }
        | undefined;

      if (!payload || payload.type !== "klarnow:tsx-snapshot") return;
      if (payload.frameId !== frameId) return;

      if (payload.error) {
        onSnapshot(null, payload.error);
        return;
      }

      if (
        typeof payload.html !== "string" ||
        typeof payload.width !== "number" ||
        typeof payload.height !== "number"
      ) {
        onSnapshot(null, "TSX snapshot payload is incomplete.");
        return;
      }

      onSnapshot({
        html: payload.html,
        width: payload.width,
        height: payload.height,
      });
    };

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [frameId, onSnapshot]);

  const srcDoc = useMemo(() => {
    const defaultExportName = extractDefaultExportFunctionName(code);
    const runtimeCode = escapeForScript(stripModuleSyntax(code));
    const componentNameRef =
      defaultExportName && /^[A-Za-z_$][\w$]*$/.test(defaultExportName)
        ? defaultExportName
        : null;

    const componentLookup = componentNameRef
      ? `
      var __ByName = (typeof ${componentNameRef} !== "undefined" && typeof ${componentNameRef} === "function")
        ? ${componentNameRef}
        : null;
    `
      : "var __ByName = null;";

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://unpkg.com/react@18/umd/react.development.js"><\/script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"><\/script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"><\/script>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; overflow: hidden; background: transparent; }
    #root { width: 100%; height: 100%; }
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-presets="typescript,react">
    ${runtimeCode}

    try {
      ${componentLookup}
      var __Candidate =
        __ByName ||
        (typeof __DefaultComponent !== "undefined" && typeof __DefaultComponent === "function" ? __DefaultComponent : null) ||
        (typeof __DefaultExport !== "undefined" && typeof __DefaultExport === "function" ? __DefaultExport : null) ||
        (typeof Poster !== "undefined" && typeof Poster === "function" ? Poster : null) ||
        (typeof App !== "undefined" && typeof App === "function" ? App : null);

      var __Root = typeof __Candidate === "function"
        ? __Candidate
        : () => React.createElement("div", { style: { color: "#f43f5e", fontFamily: "Arial, sans-serif", fontSize: "12px", padding: "12px" } }, "Unable to render TSX poster preview.");

      ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(__Root));

      function __postSnapshot() {
        var root = document.getElementById("root");
        var node = root && root.firstElementChild;
        if (!node) {
          window.parent.postMessage({
            type: "klarnow:tsx-snapshot",
            frameId: ${JSON.stringify(frameId)},
            error: "TSX preview rendered no root node.",
          }, "*");
          return;
        }

        var rect = node.getBoundingClientRect();
        window.parent.postMessage({
          type: "klarnow:tsx-snapshot",
          frameId: ${JSON.stringify(frameId)},
          html: node.outerHTML,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        }, "*");
      }

      setTimeout(function() {
        requestAnimationFrame(function() {
          requestAnimationFrame(__postSnapshot);
        });
      }, 80);
    } catch (error) {
      window.parent.postMessage({
        type: "klarnow:tsx-snapshot",
        frameId: ${JSON.stringify(frameId)},
        error: error instanceof Error ? error.message : String(error),
      }, "*");
    }
  <\/script>
</body>
</html>`;
  }, [code, frameId]);

  return (
    <div
      className={cn("overflow-hidden", className)}
      style={{
        width: Math.round(width * scale),
        height: Math.round(height * scale),
      }}
      title={name}
    >
      <iframe
        sandbox="allow-scripts allow-same-origin"
        srcDoc={srcDoc}
        title={name}
        style={{
          width,
          height,
          border: "none",
          transform: `scale(${scale})`,
          transformOrigin: "top left",
          display: "block",
        }}
      />
    </div>
  );
}
