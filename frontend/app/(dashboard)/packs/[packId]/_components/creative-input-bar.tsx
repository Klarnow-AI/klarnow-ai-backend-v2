"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  Image,
  Mic,
  Send,
  ChevronRight,
  Pencil,
  FolderPlus,
  Paperclip,
  X,
} from "@/components/icons";
import { toast } from "sonner";
import { IconButton } from "@/components/ui/icon-button";
import { CreativeInput } from "./creative-input";
import { useDynamicPopover } from "@/hooks/use-dynamic-popover";
import {
  useFloating,
  offset,
  flip,
  shift,
  autoUpdate,
} from "@floating-ui/react-dom";
import { motion, AnimatePresence } from "framer-motion";
import type { BrandContext } from "@/app/api/generate/route";
import type { PosterReferenceImage } from "@/lib/generate-poster";
import { getToken } from "@/lib/http";

const POSTER_IMAGE_MAX_FILES = 3;
const POSTER_IMAGE_MAX_BYTES = 4 * 1024 * 1024;

function parseFileTags(text: string): Record<string, string> {
  const files: Record<string, string> = {};
  const regex = /<file name="([^"]+)">([\s\S]*?)<\/file>/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const name = match[1].startsWith("/") ? match[1] : `/${match[1]}`;
    files[name] = match[2].trim();
  }
  return files;
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Could not read image file."));
    };
    reader.onerror = () => reject(new Error("Could not read image file."));
    reader.readAsDataURL(file);
  });
}

function formatFileSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)}MB`;
}

type CreativeInputBarProps = {
  apiRoute: string;
  packId?: string;
  brandContext?: BrandContext | null;
  placeholder?: string;
  onGenerate: (
    files: Record<string, string>,
    messages: { role: "user" | "assistant"; content: string }[],
  ) => void;
  onGeneratingChange?: (generating: boolean, prompt?: string | null) => void;
  disabled?: boolean;
};

export function CreativeInputBar({
  apiRoute,
  packId,
  brandContext,
  placeholder = "Type to Generate",
  onGenerate,
  onGeneratingChange,
  disabled = false,
}: CreativeInputBarProps) {
  const [input, setInput] = useState("");
  const [imageDropdownOpen, setImageDropdownOpen] = useState(false);
  const [recentSubmenuOpen, setRecentSubmenuOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [referenceImages, setReferenceImages] = useState<PosterReferenceImage[]>(
    [],
  );
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    refs: dropdownRefs,
    floatingStyles: dropdownStyles,
    isPositioned: dropdownPositioned,
  } = useDynamicPopover({
    open: imageDropdownOpen,
    placement: "top-start",
  });

  const {
    refs: submenuRefs,
    floatingStyles: submenuStyles,
    isPositioned: submenuPositioned,
  } = useFloating({
    open: recentSubmenuOpen,
    placement: "right-start",
    strategy: "fixed",
    transform: false,
    middleware: [offset(4), flip({ padding: 8 }), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const ref = dropdownRefs.reference.current;
      const subRef = submenuRefs.reference.current;
      if (
        (ref instanceof Element && ref.contains(target)) ||
        dropdownRefs.floating.current?.contains(target) ||
        (subRef instanceof Element && subRef.contains(target)) ||
        submenuRefs.floating.current?.contains(target)
      )
        return;
      setImageDropdownOpen(false);
      setRecentSubmenuOpen(false);
    }
    if (imageDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [
    imageDropdownOpen,
    dropdownRefs.reference,
    dropdownRefs.floating,
    submenuRefs.reference,
    submenuRefs.floating,
  ]);

  const sendRequest = useCallback(
    async (userContent: string, images: PosterReferenceImage[]) => {
      setIsStreaming(true);
      onGeneratingChange?.(true, userContent);
      const controller = new AbortController();

      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        const token = getToken();
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const res = await fetch(apiRoute, {
          method: "POST",
          headers,
          body: JSON.stringify({
            messages: [{ role: "user", content: userContent }],
            brandContext: brandContext ?? undefined,
            packId: packId ?? undefined,
            referenceImages: images.length > 0 ? images : undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errText = await res.text();
          let message: string;
          try {
            const parsed = JSON.parse(errText) as { error?: string };
            message = parsed.error ?? errText;
          } catch {
            message = errText;
          }
          onGeneratingChange?.(false, null);
          toast.error("Generation failed", { description: message });
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          onGeneratingChange?.(false);
          return;
        }

        const decoder = new TextDecoder();
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          accumulated += decoder.decode(value, { stream: true });
        }

        const extractedFiles = parseFileTags(accumulated);
        if (Object.keys(extractedFiles).length > 0) {
          const messages = [
            { role: "user" as const, content: userContent },
            {
              role: "assistant" as const,
              content: "Done! Your design has been generated.",
            },
          ];
          onGenerate(extractedFiles, messages);
        }
      } finally {
        setReferenceImages([]);
        setIsStreaming(false);
        onGeneratingChange?.(false, null);
        inputRef.current?.focus();
      }
    },
    [apiRoute, brandContext, onGenerate, onGeneratingChange, packId],
  );

  const handleSubmit = async (trimmed: string) => {
    if (!trimmed || isStreaming || disabled) return;
    const selectedImages = referenceImages.slice(0, POSTER_IMAGE_MAX_FILES);
    setInput("");
    await sendRequest(trimmed, selectedImages);
  };

  const handleUploadFile = () => {
    setImageDropdownOpen(false);
    setRecentSubmenuOpen(false);

    if (referenceImages.length >= POSTER_IMAGE_MAX_FILES) {
      toast.error(`You can attach up to ${POSTER_IMAGE_MAX_FILES} images.`);
      return;
    }

    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.accept = "image/*";
    fileInput.onchange = async () => {
      const allFiles = Array.from(fileInput.files ?? []);
      if (allFiles.length === 0) return;

      const remainingSlots = POSTER_IMAGE_MAX_FILES - referenceImages.length;
      if (allFiles.length > remainingSlots) {
        toast.error(
          `Only ${remainingSlots} more image${remainingSlots === 1 ? "" : "s"} can be added.`,
        );
      }

      const pickedFiles = allFiles.slice(0, Math.max(0, remainingSlots));
      const validFiles: File[] = [];

      for (const file of pickedFiles) {
        if (!file.type.toLowerCase().startsWith("image/")) {
          toast.error(`${file.name} is not an image file.`);
          continue;
        }
        if (file.size > POSTER_IMAGE_MAX_BYTES) {
          toast.error(
            `${file.name} is ${formatFileSize(file.size)}. Max size is 4.0MB per image.`,
          );
          continue;
        }
        validFiles.push(file);
      }

      if (validFiles.length === 0) return;

      try {
        const dataUrls = await Promise.all(
          validFiles.map((file) => fileToDataUrl(file)),
        );
        const nextImages: PosterReferenceImage[] = validFiles.map(
          (file, index) => ({
            name: file.name || `image-${Date.now()}-${index + 1}`,
            mimeType: file.type || "image/png",
            dataUrl: dataUrls[index],
          }),
        );
        setReferenceImages((prev) =>
          [...prev, ...nextImages].slice(0, POSTER_IMAGE_MAX_FILES),
        );
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Could not process image.";
        toast.error(message);
      }
    };
    fileInput.click();
  };

  const handleRemoveReferenceImage = (indexToRemove: number) => {
    setReferenceImages((prev) =>
      prev.filter((_, index) => index !== indexToRemove),
    );
  };

  return (
    <div className="w-full min-w-0">
      {referenceImages.length > 0 && (
        <div className="mb-2 flex w-full flex-wrap gap-2">
          {referenceImages.map((image, index) => (
            <div
              key={`${image.name}-${index}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs text-foreground"
            >
              <Paperclip className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="max-w-[190px] truncate">{image.name}</span>
              <IconButton
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Remove ${image.name}`}
                className="h-5 w-5 rounded-full p-0 text-muted-foreground hover:text-foreground"
                onClick={() => handleRemoveReferenceImage(index)}
                disabled={isStreaming || disabled}
              >
                <X className="h-3 w-3" />
              </IconButton>
            </div>
          ))}
        </div>
      )}

      <CreativeInput
        ref={inputRef}
        value={input}
        onChange={setInput}
        placeholder={placeholder}
        disabled={isStreaming || disabled}
        onSubmit={handleSubmit}
        leftAdornment={
          <div className="relative" ref={dropdownRefs.setReference}>
            <IconButton
              type="button"
              variant="ghost"
              size="md"
              aria-label="Image options"
              onClick={() => setImageDropdownOpen((o) => !o)}
              disabled={disabled || isStreaming}
            >
              <Image className="h-4 w-4" />
            </IconButton>
            {typeof document !== "undefined" &&
              createPortal(
                <AnimatePresence>
                  {imageDropdownOpen && (
                    <div
                      ref={dropdownRefs.setFloating}
                      style={{
                        ...dropdownStyles,
                        visibility: dropdownPositioned ? "visible" : "hidden",
                      }}
                    >
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: dropdownPositioned ? 1 : 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="z-50 w-56 rounded-xl border border-border bg-card py-1 shadow-lg"
                      >
                        <button
                          type="button"
                          onClick={handleUploadFile}
                          className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted/50"
                        >
                          <FolderPlus className="h-4 w-4 shrink-0 text-muted-foreground" />
                          Upload a file
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setImageDropdownOpen(false);
                            setRecentSubmenuOpen(false);
                          }}
                          className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted/50"
                        >
                          <Pencil className="h-4 w-4 shrink-0 text-muted-foreground" />
                          Draw a sketch
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setImageDropdownOpen(false);
                            setRecentSubmenuOpen(false);
                          }}
                          className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-muted-foreground transition-colors hover:bg-muted/50"
                        >
                          Connect Google Drive
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setImageDropdownOpen(false);
                            setRecentSubmenuOpen(false);
                          }}
                          className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-muted-foreground transition-colors hover:bg-muted/50"
                        >
                          Connect Microsoft OneDrive
                        </button>
                        <div
                          className="relative"
                          onMouseEnter={() => setRecentSubmenuOpen(true)}
                          onMouseLeave={() => setRecentSubmenuOpen(false)}
                        >
                          <button
                            ref={submenuRefs.setReference}
                            type="button"
                            onClick={() => setRecentSubmenuOpen((o) => !o)}
                            className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted/50"
                          >
                            Recent
                            <ChevronRight className="h-4 w-4 shrink-0" />
                          </button>
                        </div>
                      </motion.div>
                    </div>
                  )}
                </AnimatePresence>,
                document.body,
              )}
            {typeof document !== "undefined" &&
              createPortal(
                <AnimatePresence>
                  {recentSubmenuOpen && (
                    <div
                      ref={submenuRefs.setFloating}
                      style={{
                        ...submenuStyles,
                        visibility: submenuPositioned ? "visible" : "hidden",
                      }}
                    >
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: submenuPositioned ? 1 : 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="z-50 w-48 rounded-xl border border-border bg-card py-1 shadow-lg"
                      >
                        <div className="px-3 py-2 text-xs text-muted-foreground">
                          No recent files
                        </div>
                      </motion.div>
                    </div>
                  )}
                </AnimatePresence>,
                document.body,
              )}
          </div>
        }
        rightAdornment={
          <>
            <IconButton
              type="button"
              variant="ghost"
              size="md"
              aria-label="Microphone"
              disabled={disabled || isStreaming}
            >
              <Mic className="h-4 w-4" />
            </IconButton>
            <IconButton
              type="submit"
              variant="solid"
              size="md"
              aria-label="Send"
              disabled={!input.trim() || isStreaming || disabled}
            >
              <Send className="h-4 w-4" />
            </IconButton>
          </>
        }
      />
    </div>
  );
}
