"use client";

import { useEffect, useState } from "react";
import {
  CreativeTemplateCard,
  type CreativeTemplateCardAsset,
} from "./creative-template-card";
import { Image, Lock } from "@/components/icons";
import { Spinner } from "@/components/ui/page-loader";

let cachedPosterLoadingAnimationData: object | null = null;

async function loadPosterLoadingAnimationData(): Promise<object | null> {
  if (cachedPosterLoadingAnimationData) {
    return cachedPosterLoadingAnimationData;
  }

  try {
    const res = await fetch("/assets/jsons/ai-loading.json");
    if (!res.ok) return null;
    const data = await res.json();
    cachedPosterLoadingAnimationData = data;
    return data;
  } catch {
    return null;
  }
}

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

function GeneratingTile() {
  const [animationData, setAnimationData] = useState<object | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    loadPosterLoadingAnimationData()
      .then((data) => {
        if (cancelled) return;
        setAnimationData(data);
        setLoadFailed(!data);
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-w-0">
      <div className="flex aspect-[4/5] items-center justify-center min-w-0">
        {loadFailed || !animationData ? (
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-foreground" />
        ) : (
          // <Lottie
          //   animationData={animationData}
          //   loop
          //   autoplay
          //   className="h-full w-full"
          // />
          <Spinner className="h-10 w-10" />
        )}
      </div>
    </div>
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
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] gap-4">
            {group.results.map((asset, i) => (
              <div key={asset.id ?? `${asset.name}-${i}`} className="min-w-0">
                <CreativeTemplateCard
                  asset={asset}
                  onClick={() => onAssetClick(asset)}
                />
              </div>
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
          <div className="grid grid-cols-[repeat(2,minmax(0,1fr))] sm:grid-cols-[repeat(3,minmax(0,1fr))] md:grid-cols-[repeat(4,minmax(0,1fr))] gap-4">
            <GeneratingTile />
          </div>
        </div>
      )}
    </div>
  );
}
