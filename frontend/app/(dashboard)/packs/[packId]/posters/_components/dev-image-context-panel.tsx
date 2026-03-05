"use client";

import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { imageContext } from "@/api_requests/image-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const SHOW_DEV_PANEL = process.env.NODE_ENV === "development";

function formatFileSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(1)}MB`;
}

export function DevImageContextPanel() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [caption, setCaption] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasInvalidFiles = useMemo(
    () => files.some((file) => !file.type.toLowerCase().startsWith("image/")),
    [files],
  );

  if (!SHOW_DEV_PANEL) return null;

  async function uploadSelectedFiles() {
    if (files.length === 0) {
      toast.error("Choose at least one image file.");
      return;
    }
    if (hasInvalidFiles) {
      toast.error("Only image files can be uploaded to retrieval context.");
      return;
    }

    setUploading(true);
    let successCount = 0;
    let failedCount = 0;
    let firstError: string | null = null;
    const tags = tagsInput
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);

    for (const file of files) {
      try {
        await imageContext.uploadGlobal(file, {
          caption: caption.trim() || undefined,
          tags: tags.length > 0 ? tags : undefined,
        });
        successCount += 1;
      } catch (error) {
        failedCount += 1;
        if (!firstError) {
          firstError =
            error instanceof Error
              ? `${file.name}: ${error.message}`
              : `${file.name}: upload failed`;
        }
      }
    }

    if (successCount > 0) {
      toast.success(
        `Uploaded ${successCount} retrieval image${successCount === 1 ? "" : "s"} to the global index.`,
      );
    }
    if (failedCount > 0) {
      toast.error(
        `${failedCount} upload${failedCount === 1 ? "" : "s"} failed.`,
        {
          description: firstError ?? undefined,
        },
      );
    }

    setFiles([]);
    setCaption("");
    setTagsInput("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    setUploading(false);
  }

  return (
    <div className="shrink-0 border-b border-amber-200 bg-amber-50/50 px-4 py-3">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-amber-800">
          Developer Only: Retrieval Image Context Seeder
        </p>
        <p className="text-xs text-amber-900/80">
          Upload sample images into the global retrieval index used by every
          poster generation.
        </p>

        <div className="grid gap-2 md:grid-cols-3">
          <Input
            value={caption}
            onChange={(event) => setCaption(event.target.value)}
            placeholder="Optional shared caption"
            className="h-10 rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs text-amber-900"
            disabled={uploading}
          />
          <Input
            value={tagsInput}
            onChange={(event) => setTagsInput(event.target.value)}
            placeholder="Optional tags (comma-separated)"
            className="h-10 rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs text-amber-900"
            disabled={uploading}
          />
          <div />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*"
            className="max-w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs text-amber-900"
            onChange={(event) => {
              const next = Array.from(event.target.files ?? []);
              setFiles(next);
            }}
            disabled={uploading}
          />
          <Button
            size="sm"
            onClick={uploadSelectedFiles}
            disabled={uploading || files.length === 0}
          >
            {uploading ? "Uploading..." : "Upload To Global Index"}
          </Button>
        </div>

        {files.length > 0 && (
          <p className="text-xs text-amber-900/80">
            Selected {files.length} file{files.length === 1 ? "" : "s"}:{" "}
            {files.map((file) => `${file.name} (${formatFileSize(file.size)})`).join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
