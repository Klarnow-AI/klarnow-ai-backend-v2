"use client";

import { useCallback, useState } from "react";
import JSZip from "jszip";
import { saveAs } from "file-saver";
import { useProjectStore } from "@/store/useProjectStore";
import { builder } from "@/api_requests/builder";
import { Download, Globe, Loader2 } from "@/components/icons";

export function ExportButton() {
  const projectId = useProjectStore((s) => s.projectId);
  const liveUrl = useProjectStore((s) => s.liveUrl);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isUnpublishing, setIsUnpublishing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePublish = useCallback(async () => {
    if (!projectId) return;
    setIsPublishing(true);
    setError(null);
    try {
      const result = await builder.publish(projectId);
      useProjectStore.getState().setLiveUrl(result.live_url ?? null);
      useProjectStore.getState().setPublishedFiles(result.published_files ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setIsPublishing(false);
    }
  }, [projectId]);

  const handleUnpublish = useCallback(async () => {
    if (!projectId) return;
    setIsUnpublishing(true);
    setError(null);
    try {
      await builder.unpublish(projectId);
      useProjectStore.getState().setLiveUrl(null);
      useProjectStore.getState().setPublishedFiles(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unpublish failed");
    } finally {
      setIsUnpublishing(false);
    }
  }, [projectId]);

  const handleExport = useCallback(async () => {
    setIsExporting(true);
    try {
      const files = useProjectStore.getState().files;
      const zip = new JSZip();
      for (const [path, content] of Object.entries(files)) {
        const cleanPath = path.startsWith("/") ? path.slice(1) : path;
        zip.file(cleanPath, content);
      }
      const blob = await zip.generateAsync({ type: "blob" });
      saveAs(blob, "project.zip");
    } finally {
      setIsExporting(false);
    }
  }, []);

  return (
    <div className="flex items-center gap-2">
      {liveUrl ? (
        <>
          <a
            href={liveUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-sm font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
          >
            <Globe className="h-3.5 w-3.5" />
            View Live
          </a>
          <button
            onClick={handlePublish}
            disabled={isPublishing}
            className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPublishing ? "Updating..." : "Republish"}
          </button>
          <button
            onClick={handleUnpublish}
            disabled={isUnpublishing}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isUnpublishing ? "Unpublishing..." : "Unpublish"}
          </button>
        </>
      ) : (
        <button
          onClick={handlePublish}
          disabled={isPublishing || !projectId}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isPublishing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {isPublishing ? "Publishing..." : "Publish"}
        </button>
      )}

      {error && (
        <span
          className="text-xs text-destructive max-w-[200px] truncate"
          title={error}
        >
          {error}
        </span>
      )}

      <button
        onClick={handleExport}
        disabled={isExporting}
        title="Export source code as ZIP"
        className="rounded-lg p-2 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Download className="h-4 w-4" />
      </button>
    </div>
  );
}
