"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CreativeTemplateCard,
  type CreativeTemplateCardAsset,
} from "./creative-template-card";
import { Image, Lock } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";
import { inferPosterCanvasDimensions } from "@/lib/poster-canvas";

export type CreativeGenerationDisplay = {
  kind: "prompt" | "background_task";
  label: string;
  displayKey: string;
  taskLabel?: string | null;
  modeLabel?: string | null;
};

export type PromptWithResults = {
  display: CreativeGenerationDisplay;
  results: CreativeTemplateCardAsset[];
  createdAt: string;
};

type CreativeTemplateGridProps = {
  sprintDay: number | null;
  promptGroups: PromptWithResults[];
  generationDisplay: CreativeGenerationDisplay | null;
  isGenerating?: boolean;
  generationProgress?: {
    completedCount: number;
    totalCount: number;
  } | null;
  variant: "posters";
  onAssetClick: (asset: CreativeTemplateCardAsset) => void;
};

const MASONRY_AUTO_ROW_PX = 8;
const MASONRY_ESTIMATED_TILE_WIDTH_PX = 240;

function renderGroupHeader(
  display: CreativeGenerationDisplay,
  progress?: {
    completedCount: number;
    totalCount: number;
  } | null,
) {
  if (display.kind === "background_task") {
    return null;
  }

  if (display.kind === "prompt") {
    return (
      <div className="flex justify-end">
        <div
          className="inline-flex max-w-[85%] rounded-2xl rounded-tr-md px-4 py-3 bg-primary text-primary-foreground"
          style={{ width: "fit-content" }}
        >
          <p className="text-sm whitespace-pre-wrap">{display.label}</p>
        </div>
      </div>
    );
  }

  return null;
}

function MasonryTile({
  aspectRatio,
  children,
}: {
  aspectRatio: number;
  children: React.ReactNode;
}) {
  const itemRef = useRef<HTMLDivElement>(null);
  const [rowSpan, setRowSpan] = useState(() =>
    Math.max(
      1,
      Math.ceil(
        (MASONRY_ESTIMATED_TILE_WIDTH_PX * aspectRatio) / MASONRY_AUTO_ROW_PX,
      ),
    ),
  );

  useEffect(() => {
    if (!itemRef.current) return;

    const element = itemRef.current;

    const updateRowSpan = () => {
      const grid = element.parentElement;
      const itemWidth = element.clientWidth;
      if (!grid || itemWidth <= 0) return;

      const gridStyles = window.getComputedStyle(grid);
      const rowGap = Number.parseFloat(gridStyles.rowGap || "0");
      const nextRowSpan = Math.max(
        1,
        Math.ceil(
          (itemWidth * aspectRatio + rowGap) / (MASONRY_AUTO_ROW_PX + rowGap),
        ),
      );

      setRowSpan((current) =>
        current === nextRowSpan ? current : nextRowSpan,
      );
    };

    updateRowSpan();

    const resizeObserver = new ResizeObserver(updateRowSpan);
    resizeObserver.observe(element);

    return () => resizeObserver.disconnect();
  }, [aspectRatio]);

  return (
    <div
      ref={itemRef}
      className="min-w-0"
      style={{ gridRow: `span ${rowSpan} / span ${rowSpan}` }}
    >
      {children}
    </div>
  );
}

function PosterTile({
  asset,
  onAssetClick,
}: {
  asset: CreativeTemplateCardAsset;
  onAssetClick: (asset: CreativeTemplateCardAsset) => void;
}) {
  const canvas = useMemo(
    () => inferPosterCanvasDimensions(asset.name, asset.code),
    [asset.code, asset.name],
  );

  return (
    <MasonryTile aspectRatio={canvas.height / canvas.width}>
      <CreativeTemplateCard
        asset={asset}
        onClick={() => onAssetClick(asset)}
        className="h-full"
      />
    </MasonryTile>
  );
}

function GeneratingTile() {
  return (
    <MasonryTile aspectRatio={5 / 4}>
      <div className="flex h-full items-center justify-center min-w-0 rounded-xl bg-muted/20">
        <Spinner className="h-10 w-10" />
      </div>
    </MasonryTile>
  );
}

export function CreativeTemplateGrid({
  sprintDay,
  promptGroups,
  generationDisplay,
  isGenerating = false,
  generationProgress = null,
  onAssetClick,
}: CreativeTemplateGridProps) {
  const hasCompletedDay0To3 = (sprintDay ?? 0) >= 4;
  const hasContent = promptGroups.length > 0 || isGenerating;

  if (!hasCompletedDay0To3) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-4">
          <Lock className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground mb-1">
          Complete Step 0–3 to unlock starter templates
        </p>
        <p className="max-w-sm text-sm text-muted-foreground leading-relaxed">
          Finish your sprint setup (Steps 0–3) to access and create posters and
          flyers.
        </p>
      </div>
    );
  }

  if (!hasContent) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted mb-4">
          <Image className="h-8 w-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-medium text-foreground mb-1">
          No posters yet
        </p>
        <p className="max-w-sm text-sm text-muted-foreground leading-relaxed">
          Type a prompt in the bar below to create your first poster or flyer.
        </p>
      </div>
    );
  }

  const activeDisplayKey = generationDisplay?.displayKey ?? null;
  const hasActiveGroup =
    isGenerating &&
    activeDisplayKey !== null &&
    promptGroups.some((group) => group.display.displayKey === activeDisplayKey);

  return (
    <div className="flex flex-col gap-8 p-4 min-w-0 w-full">
      {promptGroups.map((group) => (
        <div
          key={group.createdAt + group.display.displayKey}
          className="space-y-4 min-w-0"
        >
          {renderGroupHeader(
            group.display,
            isGenerating && group.display.displayKey === activeDisplayKey
              ? generationProgress
              : null,
          )}
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] auto-rows-[8px] gap-4 grid-flow-dense items-start">
            {group.results.map((asset, i) => (
              <PosterTile
                key={asset.id ?? `${asset.name}-${i}`}
                asset={asset}
                onAssetClick={onAssetClick}
              />
            ))}
            {isGenerating && group.display.displayKey === activeDisplayKey && (
              <GeneratingTile />
            )}
          </div>
        </div>
      ))}
      {isGenerating && generationDisplay && !hasActiveGroup && (
        <div className="space-y-4 min-w-0">
          {renderGroupHeader(generationDisplay, generationProgress)}
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] auto-rows-[8px] gap-4 grid-flow-dense items-start">
            <GeneratingTile />
          </div>
        </div>
      )}
    </div>
  );
}
