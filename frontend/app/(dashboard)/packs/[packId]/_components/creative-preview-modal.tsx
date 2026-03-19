"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ChevronLeft,
  Download,
  Trash2,
  X,
  Pencil,
} from "@/components/icons";
import { useMediaQuery } from "@/hooks/use-media-query";
import { Dialog } from "@/components/ui/dialog";
import { IconButton } from "@/components/ui/icon-button";
import { Button } from "@/components/ui/button";
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

type CreativePreviewModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset: CreativePreviewAsset | null;
  variant: "posters";
  onDelete?: (assetId: string) => void | Promise<void>;
  onCanvasSave?: (
    asset: CreativePreviewAsset,
    code: string,
  ) => void | Promise<void>;
};

type DragState = {
  id: string;
  startClientX: number;
  startClientY: number;
  startTranslateX: number;
  startTranslateY: number;
};

function isLeafTextElement(node: Element | null): node is HTMLElement {
  if (!(node instanceof HTMLElement)) return false;
  if (["SCRIPT", "STYLE", "IMG", "SVG", "PATH", "BR", "HR"].includes(node.tagName)) {
    return false;
  }
  const elementChildren = Array.from(node.children);
  if (elementChildren.some((child) => child.tagName !== "BR")) {
    return false;
  }
  return Array.from(node.childNodes).some((child) => {
    if (child.nodeType === Node.TEXT_NODE) {
      return (child.textContent || "").trim().length > 0;
    }
    return child instanceof HTMLElement && child.tagName === "BR";
  });
}

function prepareEditableCanvas(root: HTMLElement) {
  let nextId = 1;
  const elements = root.querySelectorAll("*");
  for (const element of elements) {
    if (!(element instanceof HTMLElement)) continue;
    element.removeAttribute("data-klarnow-editable-id");
    element.removeAttribute("data-klarnow-selected");
    element.removeAttribute("data-klarnow-editing");
    element.removeAttribute("contenteditable");
    element.removeAttribute("spellcheck");
    element.style.outline = "";
    element.style.outlineColor = "";
    element.style.cursor = "";
    element.style.userSelect = "";
    if (!isLeafTextElement(element)) continue;
    element.dataset.klarnowEditableId = String(nextId++);
    element.style.cursor = "move";
    element.style.userSelect = "none";
  }
}

function applySelectionStyles(
  root: HTMLElement,
  selectedId: string | null,
  editingId: string | null,
) {
  const elements = root.querySelectorAll<HTMLElement>("[data-klarnow-editable-id]");
  for (const element of elements) {
    const isSelected = element.dataset.klarnowEditableId === selectedId;
    const isEditing = element.dataset.klarnowEditableId === editingId;
    element.dataset.klarnowSelected = isSelected ? "true" : "false";
    element.dataset.klarnowEditing = isEditing ? "true" : "false";
    element.style.outline = isSelected || isEditing ? "2px solid" : "";
    element.style.outlineColor = isEditing ? "#14b8a6" : "#2563eb";
    element.style.outlineOffset = isSelected || isEditing ? "2px" : "";
  }
}

function escapeCanvasHtmlForTsx(html: string): string {
  return JSON.stringify(html);
}

function buildCanvasEditedTsx(
  html: string,
  width: number,
  height: number,
): string {
  return `const html = ${escapeCanvasHtmlForTsx(html)};

export default function Poster() {
  return (
    <div
      style={{ width: ${width}, height: ${height}, overflow: "hidden" }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
`;
}

function sanitizeEditableHtml(root: HTMLElement): string {
  const clone = root.cloneNode(true) as HTMLElement;
  const elements = [clone, ...Array.from(clone.querySelectorAll<HTMLElement>("*"))];
  for (const element of elements) {
    for (const attr of Array.from(element.attributes)) {
      if (attr.name.startsWith("data-klarnow-")) {
        element.removeAttribute(attr.name);
      }
    }
    element.removeAttribute("contenteditable");
    element.removeAttribute("spellcheck");
    element.style.outline = "";
    element.style.outlineColor = "";
    element.style.outlineOffset = "";
    element.style.cursor = "";
    element.style.userSelect = "";
  }
  return clone.outerHTML;
}

export function CreativePreviewModal({
  open,
  onOpenChange,
  asset,
  variant,
  onDelete,
  onCanvasSave,
}: CreativePreviewModalProps) {
  const posterRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const editableCanvasRef = useRef<HTMLDivElement>(null);
  const dragStateRef = useRef<DragState | null>(null);
  const [scale, setScale] = useState(1);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isCanvasEditing, setIsCanvasEditing] = useState(false);
  const [isCanvasSaving, setIsCanvasSaving] = useState(false);
  const [canvasHtml, setCanvasHtml] = useState<string | null>(null);
  const [selectedEditableId, setSelectedEditableId] = useState<string | null>(null);
  const [inlineEditingId, setInlineEditingId] = useState<string | null>(null);
  const [tsxSnapshot, setTsxSnapshot] = useState<TsxSandboxSnapshot | null>(null);
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
    const w = el.clientWidth - 32;
    const h = el.clientHeight - 48;
    const s = Math.min(1, w / canvas.width, h / canvas.height);
    setScale(Math.max(0.1, s));
  }, [canvas.height, canvas.width]);

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

  useEffect(() => {
    setTsxSnapshot(null);
    setTsxSnapshotError(null);
    setIsCanvasEditing(false);
    setIsCanvasSaving(false);
    setCanvasHtml(null);
    setSelectedEditableId(null);
    setInlineEditingId(null);
  }, [asset?.name, asset?.code]);

  useEffect(() => {
    if (open) return;
    setIsCanvasEditing(false);
    setIsCanvasSaving(false);
    setCanvasHtml(null);
    setSelectedEditableId(null);
    setInlineEditingId(null);
  }, [open]);

  const editableSourceHtml = useMemo(() => {
    if (!asset) return null;
    if (isTsxAsset(asset.name)) {
      return tsxSnapshot ? patchPosterHtmlForImages(tsxSnapshot.html) : null;
    }
    if (isHtmlAsset(asset.name)) {
      return patchPosterHtmlForImages(asset.code);
    }
    return null;
  }, [asset, tsxSnapshot]);

  useEffect(() => {
    if (!isCanvasEditing) {
      setCanvasHtml(null);
      setSelectedEditableId(null);
      setInlineEditingId(null);
      return;
    }
    setCanvasHtml(editableSourceHtml);
  }, [editableSourceHtml, isCanvasEditing]);

  useEffect(() => {
    const root = editableCanvasRef.current?.firstElementChild;
    if (!(root instanceof HTMLElement) || !isCanvasEditing) return;
    prepareEditableCanvas(root);
  }, [canvasHtml, isCanvasEditing]);

  useEffect(() => {
    const root = editableCanvasRef.current?.firstElementChild;
    if (!(root instanceof HTMLElement) || !isCanvasEditing) return;
    applySelectionStyles(root, selectedEditableId, inlineEditingId);
  }, [inlineEditingId, isCanvasEditing, selectedEditableId]);

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
    } catch (e) {
      console.error("PNG download failed:", e);
      toast.error("Download failed", {
        description: e instanceof Error ? e.message : "Unexpected error",
      });
    } finally {
      setIsDownloading(false);
    }
  }, [asset, isDownloading, tsxSnapshot, tsxSnapshotError, variant]);

  const handleDelete = useCallback(() => {
    if (asset?.id && onDelete) {
      onDelete(asset.id);
      onOpenChange(false);
    }
  }, [asset?.id, onDelete, onOpenChange]);

  const selectEditableElement = useCallback((element: HTMLElement | null) => {
    const root = editableCanvasRef.current?.firstElementChild;
    const nextId = element?.dataset.klarnowEditableId ?? null;
    setSelectedEditableId(nextId);
    if (root instanceof HTMLElement) {
      applySelectionStyles(root, nextId, inlineEditingId);
    }
  }, [inlineEditingId]);

  const stopInlineEditing = useCallback(
    (nextSelectedId?: string | null) => {
      const root = editableCanvasRef.current?.firstElementChild;
      const resolvedSelectedId =
        nextSelectedId === undefined ? selectedEditableId : nextSelectedId;
      if (root instanceof HTMLElement && inlineEditingId) {
        const activeElement = root.querySelector<HTMLElement>(
          `[data-klarnow-editable-id="${inlineEditingId}"]`,
        );
        if (activeElement) {
          activeElement.contentEditable = "false";
          activeElement.removeAttribute("spellcheck");
          activeElement.style.cursor = "move";
          activeElement.style.userSelect = "none";
          activeElement.blur();
        }
        applySelectionStyles(root, resolvedSelectedId ?? null, null);
      }
      setInlineEditingId(null);
    },
    [inlineEditingId, selectedEditableId],
  );

  const beginInlineEditing = useCallback(
    (element: HTMLElement | null) => {
      const root = editableCanvasRef.current?.firstElementChild;
      const nextId = element?.dataset.klarnowEditableId ?? null;
      if (!(root instanceof HTMLElement) || !element || !nextId) return;

      if (inlineEditingId && inlineEditingId !== nextId) {
        const activeElement = root.querySelector<HTMLElement>(
          `[data-klarnow-editable-id="${inlineEditingId}"]`,
        );
        if (activeElement) {
          activeElement.contentEditable = "false";
          activeElement.removeAttribute("spellcheck");
          activeElement.style.cursor = "move";
          activeElement.style.userSelect = "none";
          activeElement.blur();
        }
      }

      setSelectedEditableId(nextId);
      setInlineEditingId(nextId);
      element.contentEditable = "true";
      element.setAttribute("spellcheck", "false");
      element.style.cursor = "text";
      element.style.userSelect = "text";
      applySelectionStyles(root, nextId, nextId);

      window.requestAnimationFrame(() => {
        element.focus();
        const selection = window.getSelection();
        if (!selection) return;
        const range = document.createRange();
        range.selectNodeContents(element);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
      });
    },
    [inlineEditingId],
  );

  const handleCanvasPointerMove = useCallback(
    (event: PointerEvent) => {
      const state = dragStateRef.current;
      const root = editableCanvasRef.current?.firstElementChild;
      if (!state || !(root instanceof HTMLElement)) return;
      const target = root.querySelector<HTMLElement>(
        `[data-klarnow-editable-id="${state.id}"]`,
      );
      if (!target) return;

      const deltaX = (event.clientX - state.startClientX) / scale;
      const deltaY = (event.clientY - state.startClientY) / scale;
      const nextTranslateX = state.startTranslateX + deltaX;
      const nextTranslateY = state.startTranslateY + deltaY;

      if (!target.dataset.klarnowBaseTransform) {
        target.dataset.klarnowBaseTransform = target.style.transform || "";
      }
      if (!target.dataset.klarnowBaseDisplay) {
        target.dataset.klarnowBaseDisplay = target.style.display || "";
      }
      if (getComputedStyle(target).display === "inline") {
        target.style.display = "inline-block";
      }

      target.dataset.klarnowTranslateX = String(nextTranslateX);
      target.dataset.klarnowTranslateY = String(nextTranslateY);
      const baseTransform = target.dataset.klarnowBaseTransform || "";
      target.style.transform =
        `${baseTransform} translate(${Math.round(nextTranslateX)}px, ${Math.round(nextTranslateY)}px)`.trim();
    },
    [scale],
  );

  const handleCanvasPointerUp = useCallback(() => {
    dragStateRef.current = null;
    window.removeEventListener("pointermove", handleCanvasPointerMove);
    window.removeEventListener("pointerup", handleCanvasPointerUp);
  }, [handleCanvasPointerMove]);

  useEffect(() => {
    return () => {
      window.removeEventListener("pointermove", handleCanvasPointerMove);
      window.removeEventListener("pointerup", handleCanvasPointerUp);
    };
  }, [handleCanvasPointerMove, handleCanvasPointerUp]);

  const handleCanvasPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isCanvasEditing) return;
      const root = editableCanvasRef.current?.firstElementChild;
      if (!(root instanceof HTMLElement)) return;
      const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
        "[data-klarnow-editable-id]",
      );
      if (inlineEditingId) {
        const activeElement = root.querySelector<HTMLElement>(
          `[data-klarnow-editable-id="${inlineEditingId}"]`,
        );
        if (
          activeElement &&
          target?.dataset.klarnowEditableId === inlineEditingId
        ) {
          selectEditableElement(activeElement);
          return;
        }
        stopInlineEditing(target?.dataset.klarnowEditableId ?? null);
      }
      if (!target) {
        selectEditableElement(null);
        return;
      }

      selectEditableElement(target);
      const translateX = Number(target.dataset.klarnowTranslateX || "0");
      const translateY = Number(target.dataset.klarnowTranslateY || "0");
      dragStateRef.current = {
        id: target.dataset.klarnowEditableId || "",
        startClientX: event.clientX,
        startClientY: event.clientY,
        startTranslateX: Number.isFinite(translateX) ? translateX : 0,
        startTranslateY: Number.isFinite(translateY) ? translateY : 0,
      };
      window.addEventListener("pointermove", handleCanvasPointerMove);
      window.addEventListener("pointerup", handleCanvasPointerUp, {
        once: true,
      });
      event.preventDefault();
    },
    [
      handleCanvasPointerMove,
      handleCanvasPointerUp,
      inlineEditingId,
      isCanvasEditing,
      selectEditableElement,
      stopInlineEditing,
    ],
  );

  const handleCanvasDoubleClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (!isCanvasEditing) return;
      const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
        "[data-klarnow-editable-id]",
      );
      if (!target) return;
      selectEditableElement(target);
      beginInlineEditing(target);
      event.preventDefault();
      event.stopPropagation();
    },
    [beginInlineEditing, isCanvasEditing, selectEditableElement],
  );

  const handleCanvasKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
        "[data-klarnow-editable-id]",
      );
      if (!target || target.dataset.klarnowEditableId !== inlineEditingId) {
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        stopInlineEditing(target.dataset.klarnowEditableId ?? null);
      }
    },
    [inlineEditingId, stopInlineEditing],
  );

  const handleCanvasBlurCapture = useCallback(
    (event: React.FocusEvent<HTMLDivElement>) => {
      const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
        "[data-klarnow-editable-id]",
      );
      if (!target || target.dataset.klarnowEditableId !== inlineEditingId) {
        return;
      }
      const nextFocus = event.relatedTarget;
      if (nextFocus instanceof Node && target.contains(nextFocus)) {
        return;
      }
      stopInlineEditing(target.dataset.klarnowEditableId ?? null);
    },
    [inlineEditingId, stopInlineEditing],
  );

  const handleToggleCanvasEdit = useCallback(() => {
    if (isCanvasEditing) {
      stopInlineEditing(selectedEditableId);
      setIsCanvasEditing(false);
      return;
    }
    if (!editableSourceHtml) {
      toast.error("Canvas edit unavailable", {
        description: isTsxAsset(asset?.name || "")
          ? tsxSnapshotError || "Poster preview is still loading. Try again in a moment."
          : "This asset format is not ready for canvas editing.",
      });
      return;
    }
    setIsCanvasEditing(true);
  }, [
    asset?.name,
    editableSourceHtml,
    isCanvasEditing,
    selectedEditableId,
    stopInlineEditing,
    tsxSnapshotError,
  ]);

  const handleCancelCanvasEdit = useCallback(() => {
    window.removeEventListener("pointermove", handleCanvasPointerMove);
    window.removeEventListener("pointerup", handleCanvasPointerUp);
    dragStateRef.current = null;
    stopInlineEditing(selectedEditableId);
    setIsCanvasEditing(false);
  }, [
    handleCanvasPointerMove,
    handleCanvasPointerUp,
    selectedEditableId,
    stopInlineEditing,
  ]);

  const handleSaveCanvasEdit = useCallback(async () => {
    if (!asset || !onCanvasSave || !editableCanvasRef.current) return;
    const root = editableCanvasRef.current.firstElementChild;
    if (!(root instanceof HTMLElement)) {
      toast.error("Save failed", {
        description: "No editable poster content is available yet.",
      });
      return;
    }

    setIsCanvasSaving(true);
    try {
      stopInlineEditing(selectedEditableId);
      const sanitizedHtml = sanitizeEditableHtml(root);
      const code = buildCanvasEditedTsx(sanitizedHtml, canvas.width, canvas.height);
      await onCanvasSave(asset, code);
      setIsCanvasEditing(false);
    } catch (error) {
      toast.error("Save failed", {
        description: error instanceof Error ? error.message : "Unexpected error",
      });
    } finally {
      setIsCanvasSaving(false);
    }
  }, [
    asset,
    canvas.height,
    canvas.width,
    onCanvasSave,
    selectedEditableId,
    stopInlineEditing,
  ]);

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
      <IconButton
        type="button"
        variant="solid"
        size="lg"
        aria-label={isCanvasEditing ? "Exit canvas edit" : "Canvas edit"}
        onClick={handleToggleCanvasEdit}
        className={`text-white hover:opacity-90 ${
          isCanvasEditing ? "bg-blue-600" : "bg-black/25"
        }`}
      >
        <Pencil className="h-5 w-5" />
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
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <div
        className="fixed inset-0 z-50 flex flex-col bg-background pt-safe pl-safe pr-safe pb-safe"
        onClick={(e) => e.stopPropagation()}
      >
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
          {isCanvasEditing && canvasHtml ? (
            <div
              ref={editableCanvasRef}
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
                touchAction: "none",
              }}
              onPointerDown={handleCanvasPointerDown}
              onDoubleClick={handleCanvasDoubleClick}
              onKeyDown={handleCanvasKeyDown}
              onBlurCapture={handleCanvasBlurCapture}
              dangerouslySetInnerHTML={{
                __html: canvasHtml,
              }}
            />
          ) : isTsx ? (
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
              style={{ width: canvas.width, height: canvas.height, minHeight: 200 }}
            >
              <p className="text-sm text-muted-foreground p-4 text-center">
                Unsupported format.
              </p>
            </div>
          )}
        </div>

        {isCanvasEditing && (
          <div
            className={`pointer-events-none absolute inset-x-0 z-10 flex justify-center px-4 ${
              isMobile ? "bottom-36 pb-safe" : "bottom-6"
            }`}
          >
            <div className="pointer-events-auto flex w-full max-w-2xl items-center justify-between gap-4 rounded-2xl border border-white/15 bg-black/70 px-4 py-3 text-white shadow-2xl backdrop-blur">
              <p className="text-sm text-white/80">
                Click to select, double-click text to edit, drag to move.
              </p>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancelCanvasEdit}
                  disabled={isCanvasSaving}
                  className="border-white/20 bg-white/5 text-white hover:bg-white/10"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  onClick={handleSaveCanvasEdit}
                  disabled={isCanvasSaving || !onCanvasSave}
                  className="bg-white text-black hover:bg-white/90"
                >
                  {isCanvasSaving ? "Saving..." : "Save Edit"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
}
